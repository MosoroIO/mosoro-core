#!/usr/bin/env python3
# Copyright 2026 Mosoro Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""
Mosoro Main Edge Agent with Auto-Discovery
==========================================

Discovers vendor adapters in two ways (in priority order):

1. **Entry-point discovery** — Adapters installed via pip that register under
   the ``mosoro.adapters`` entry point group (e.g., mosoro-adapters-community).
2. **Filesystem discovery** — Adapters placed directly in the local
   ``agents/adapters/`` directory (useful for development or custom adapters).

Robot configuration can be provided in two ways:

- **robots.yaml** (preferred) — A single file listing all robots and their
  connection details.  Set ``ROBOTS_YAML_PATH`` env var or place a
  ``robots.yaml`` in the working directory.
- **Single config.yaml** (legacy) — One YAML file per robot, passed via
  ``CONFIG_PATH`` env var or as a CLI argument.

Naming convention for filesystem adapters:
- File:    locus_adapter.py
- Class:   LocusAdapter (must inherit from BaseMosoroAdapter)
"""

import asyncio
import importlib
import inspect
import json
import logging
import os
import pkgutil
import signal
import ssl
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from paho.mqtt import client as mqtt

from agents.adapters.base_adapter import BaseMosoroAdapter
from mosoro_core.models import MosoroMessage, MosoroPayload

logger = logging.getLogger("mosoro.agent")


# ---------------------------------------------------------------------------
# robots.yaml loader
# ---------------------------------------------------------------------------


def load_robots_yaml(path: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
    """Load robot configurations from a robots.yaml file.

    Resolution order for the file path:
        1. Explicit *path* argument
        2. ``ROBOTS_YAML_PATH`` environment variable
        3. ``robots.yaml`` in the current working directory

    Returns ``None`` if no robots.yaml is found (caller should fall back to
    the legacy single-config approach).  Returns a list of robot config dicts
    on success.
    """
    candidates: List[str] = []
    if path:
        candidates.append(path)
    env_path = os.environ.get("ROBOTS_YAML_PATH")
    if env_path:
        candidates.append(env_path)
    candidates.append(os.path.join(os.getcwd(), "robots.yaml"))

    robots_file: Optional[str] = None
    for candidate in candidates:
        if os.path.isfile(candidate):
            robots_file = candidate
            break

    if robots_file is None:
        return None

    try:
        with open(robots_file, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        robots = data.get("robots")
        if not isinstance(robots, list):
            logger.error("robots.yaml must contain a 'robots' list at the top level.")
            return None
        logger.info("Loaded %d robot(s) from %s", len(robots), robots_file)
        return robots
    except Exception as exc:
        logger.error("Failed to load robots.yaml from %s: %s", robots_file, exc)
        return None


def _robot_entry_to_config(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a robots.yaml entry into the config dict expected by
    :class:`MosoroEdgeAgent`.

    A robots.yaml entry looks like::

        - id: locus-001
          vendor: locus
          api_base_url: "http://192.168.1.100:8080/api"
          api_key: "key"

    The legacy config.yaml format expected by the agent has ``robot_id`` and
    ``vendor`` at the top level plus arbitrary vendor-specific keys.  This
    helper simply renames ``id`` → ``robot_id`` and passes everything else
    through.
    """
    config = dict(entry)
    if "id" in config:
        config["robot_id"] = config.pop("id")
    return config


class MosoroEdgeAgent:
    """Main Mosoro Edge Agent with automatic adapter discovery."""

    def __init__(
        self,
        config_path: str = "config.yaml",
        config_dict: Optional[Dict[str, Any]] = None,
    ):
        # Accept either a file path (legacy) or a pre-built config dict
        # (from robots.yaml).  config_dict takes precedence when provided.
        if config_dict is not None:
            self.config = config_dict
            logger.info(
                "Using provided config for robot %s (%s)",
                config_dict.get("robot_id"),
                config_dict.get("vendor"),
            )
        else:
            self.config = self._load_config(config_path)
        self.robot_id: str = self.config["robot_id"]
        self.vendor: str = self.config["vendor"].lower()

        # Auto-discover and load the correct adapter
        self.adapter = self._discover_and_load_adapter()

        # MQTT Configuration
        self.mqtt_broker: str = os.environ.get(
            "MQTT_BROKER_HOST", self.config.get("mqtt_broker", "localhost")
        )
        self.mqtt_port: int = int(
            os.environ.get("MQTT_BROKER_PORT", self.config.get("mqtt_port", 8883))
        )
        self.mqtt_use_tls: bool = os.environ.get(
            "MQTT_USE_TLS", str(self.config.get("mqtt_use_tls", True))
        ).lower() in ("true", "1", "yes")

        # MQTT Client
        self.client = mqtt.Client(client_id=f"mosoro-agent-{self.robot_id}")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        # Configure TLS/mTLS if enabled
        if self.mqtt_use_tls:
            self._configure_tls()

        self.running = True
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _load_config(self, path: str) -> Dict[str, Any]:
        """Load and validate YAML configuration."""
        try:
            with open(path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.info(
                f"Loaded config for robot {config.get('robot_id')} ({config.get('vendor')})"
            )
            return config
        except Exception as e:
            logger.error(f"Failed to load config from {path}: {e}")
            sys.exit(1)

    def _configure_tls(self):
        """Configure TLS/mTLS for secure MQTT communication."""
        ca_cert = os.environ.get(
            "MQTT_CA_CERT", self.config.get("mqtt_ca_cert", "/run/secrets/mqtt_ca_cert")
        )
        client_cert = os.environ.get("MQTT_CLIENT_CERT", self.config.get("mqtt_client_cert"))
        client_key = os.environ.get("MQTT_CLIENT_KEY", self.config.get("mqtt_client_key"))

        try:
            self.client.tls_set_context(self._create_ssl_context(ca_cert, client_cert, client_key))
            logger.info(f"TLS configured for agent {self.robot_id} (ca={ca_cert})")
        except FileNotFoundError as e:
            logger.warning(f"TLS certificate not found: {e}. Falling back to non-TLS.")
            self.mqtt_use_tls = False
        except (ValueError, OSError) as e:
            # TLS 1.3 minimum_version enforcement may fail on older OpenSSL builds.
            # Safe to fall back in dev; Docker prod has a current OpenSSL.
            logger.warning(
                f"TLS not supported by this OpenSSL build: {e}. Falling back to non-TLS."
            )
            self.mqtt_use_tls = False
        except Exception as e:
            logger.error(f"Failed to configure TLS: {e}")
            sys.exit(1)

    @staticmethod
    def _create_ssl_context(
        ca_cert: str,
        client_cert: Optional[str] = None,
        client_key: Optional[str] = None,
    ) -> ssl.SSLContext:
        """Create an SSL context enforcing TLS 1.3."""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.load_verify_locations(ca_cert)
        if client_cert and client_key:
            context.load_cert_chain(certfile=client_cert, keyfile=client_key)
        return context

    def _discover_and_load_adapter(self) -> BaseMosoroAdapter:
        """Discover and instantiate the correct adapter for the configured vendor.

        Discovery order:
            1. Entry-point registry (pip-installed adapter packages)
            2. Local filesystem (agents/adapters/ directory)
        """
        # --- Strategy 1: Entry-point discovery (pip-installed adapters) ---
        try:
            from mosoro_core.adapter_registry import discover_adapters

            registered = discover_adapters()
            if self.vendor in registered:
                adapter_class = registered[self.vendor]
                adapter_instance = adapter_class(self.robot_id, self.config)
                logger.info(
                    "Loaded adapter '%s' for robot %s via entry point.",
                    adapter_class.__name__,
                    self.robot_id,
                )
                return adapter_instance
        except Exception as e:
            logger.debug("Entry-point adapter discovery failed: %s", e)

        # --- Strategy 2: Filesystem discovery (local adapters/ directory) ---
        adapters_package = "agents.adapters"
        package_path = Path(__file__).parent.parent / "adapters"

        for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
            if not module_name.endswith("_adapter"):
                continue

            try:
                module = importlib.import_module(f"{adapters_package}.{module_name}")

                # Find any class in the module that inherits from BaseMosoroAdapter
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, BaseMosoroAdapter)
                        and obj != BaseMosoroAdapter
                        and name.lower().startswith(self.vendor)
                    ):
                        adapter_instance = obj(self.robot_id, self.config)
                        logger.info(
                            "Loaded adapter '%s' for robot %s via filesystem.",
                            name,
                            self.robot_id,
                        )
                        return adapter_instance

            except Exception as e:
                logger.warning(f"Failed to load module {module_name}: {e}")

        # --- No adapter found ---
        logger.error(
            "No adapter found for vendor '%s'. "
            "Install an adapter package (e.g., pip install mosoro-adapters-community) "
            "or place a %s_adapter.py file in agents/adapters/ "
            "with a class inheriting from BaseMosoroAdapter.",
            self.vendor,
            self.vendor,
        )
        sys.exit(1)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")
            cmd_topic = f"mosoro/v1/agents/{self.robot_id}/commands"
            client.subscribe(cmd_topic)
            logger.info(f"Subscribed to commands: {cmd_topic}")
            self.publish_birth()
        else:
            logger.error(f"Failed to connect to MQTT, return code: {rc}")

    def on_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected from MQTT (rc={rc})")

    def on_message(self, client, userdata, msg):
        """Handle incoming commands."""
        try:
            command = json.loads(msg.payload.decode())
            asyncio.create_task(self.adapter.handle_command(command))
        except Exception as e:
            logger.error(f"Failed to process command: {e}")

    def publish_birth(self):
        birth_msg = MosoroMessage(
            robot_id=self.robot_id,
            vendor=self.vendor,
            type="birth",
            payload=MosoroPayload(status="idle", health="starting"),
        )
        topic = f"mosoro/v1/agents/{self.robot_id}/birth"
        self.client.publish(topic, birth_msg.model_dump_json(), qos=1, retain=True)
        logger.info(f"Published birth message on {topic}")

    async def polling_loop(self):
        """Main polling loop."""
        while self.running:
            try:
                message = await self.adapter.get_normalized_status()
                topic = f"mosoro/v1/agents/{self.robot_id}/status"
                self.client.publish(topic, message.model_dump_json(), qos=1)
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")

            await asyncio.sleep(self.config.get("poll_interval", 5.0))

    def _shutdown(self, *args):
        logger.info("Shutting down Mosoro edge agent...")
        self.running = False
        if hasattr(self.adapter, "disconnect"):
            asyncio.create_task(self.adapter.disconnect())
        self.client.disconnect()

    def run(self):
        """Start the agent."""
        self.client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
        self.client.loop_start()

        try:
            asyncio.run(self.polling_loop())
        except KeyboardInterrupt:
            pass
        finally:
            self.client.loop_stop()
            logger.info("Mosoro edge agent stopped.")


def run_multi(robots_yaml_path: Optional[str] = None) -> None:
    """Launch one agent per robot defined in robots.yaml.

    Each agent runs its polling loop concurrently via :func:`asyncio.gather`.
    Falls back to the legacy single-config approach when no robots.yaml is
    found.
    """
    robots = load_robots_yaml(robots_yaml_path)
    if robots is None:
        # Fallback: legacy single-config mode
        config_path = os.environ.get("CONFIG_PATH", "config.yaml")
        logger.info("No robots.yaml found — falling back to single config: %s", config_path)
        agent = MosoroEdgeAgent(config_path=config_path)
        agent.run()
        return

    if not robots:
        logger.error("robots.yaml is empty — no robots to start.")
        sys.exit(1)

    agents: List[MosoroEdgeAgent] = []
    for entry in robots:
        config = _robot_entry_to_config(entry)
        robot_id = config.get("robot_id", "unknown")
        try:
            agent = MosoroEdgeAgent(config_dict=config)
            agents.append(agent)
            logger.info("Prepared agent for robot %s (vendor=%s)", robot_id, config.get("vendor"))
        except Exception as exc:
            logger.error("Failed to create agent for robot %s: %s", robot_id, exc)

    if not agents:
        logger.error("No agents could be created. Exiting.")
        sys.exit(1)

    # Connect all agents to MQTT
    for agent in agents:
        agent.client.connect(agent.mqtt_broker, agent.mqtt_port, keepalive=60)
        agent.client.loop_start()

    async def _run_all() -> None:
        await asyncio.gather(*(a.polling_loop() for a in agents))

    try:
        asyncio.run(_run_all())
    except KeyboardInterrupt:
        pass
    finally:
        for agent in agents:
            agent.running = False
            agent.client.loop_stop()
        logger.info("All Mosoro edge agents stopped.")


if __name__ == "__main__":
    # Priority: robots.yaml (multi-robot) → single config.yaml (legacy)
    robots_yaml_arg = None
    config_path_arg = None

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.endswith("robots.yaml") or arg.endswith("robots.yml"):
            robots_yaml_arg = arg
        else:
            config_path_arg = arg

    # Try robots.yaml first
    robots = load_robots_yaml(robots_yaml_arg)
    if robots is not None:
        run_multi(robots_yaml_arg)
    else:
        # Legacy single-config mode
        config_path = config_path_arg or os.environ.get("CONFIG_PATH", "config.yaml")
        agent = MosoroEdgeAgent(config_path=config_path)
        agent.run()
