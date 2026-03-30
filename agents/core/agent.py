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
from typing import Any, Dict, Optional

import yaml
from paho.mqtt import client as mqtt

from agents.adapters.base_adapter import BaseMosoroAdapter
from mosoro_core.models import MosoroMessage, MosoroPayload

logger = logging.getLogger("mosoro.agent")


class MosoroEdgeAgent:
    """Main Mosoro Edge Agent with automatic adapter discovery."""

    def __init__(self, config_path: str = "config.yaml"):
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
            self.client.tls_set(
                ca_certs=ca_cert,
                certfile=client_cert,
                keyfile=client_key,
                tls_version=ssl.PROTOCOL_TLS_CLIENT,
            )
            # Enforce TLS 1.3 minimum
            self.client.tls_set_context(self._create_ssl_context(ca_cert, client_cert, client_key))
            logger.info(f"TLS configured for agent {self.robot_id} (ca={ca_cert})")
        except FileNotFoundError as e:
            logger.warning(f"TLS certificate not found: {e}. Falling back to non-TLS.")
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
            payload=MosoroPayload(status="online", health="starting"),
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


if __name__ == "__main__":
    config_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.environ.get("CONFIG_PATH", "config.yaml")
    )
    agent = MosoroEdgeAgent(config_path=config_path)
    agent.run()
