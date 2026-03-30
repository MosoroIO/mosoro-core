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
Mosoro Central Gateway
=======================

MQTT-based hub and lightweight rules engine that receives normalized
MosoroMessage from all edge agents and routes/translates them between robots.

Subscribes to:
    mosoro/v1/agents/+/status
    mosoro/v1/agents/+/events
    mosoro/v1/agents/+/birth

Publishes to:
    mosoro/v1/agents/{target_id}/commands
    mosoro/v1/traffic/yield
    mosoro/v1/traffic/update
"""

import asyncio
import json
import logging
import os
import signal
import sys
from typing import Any, Dict, List
from uuid import uuid4

import yaml
from paho.mqtt import client as mqtt

from gateway.state import FleetStateStore
from mosoro_core.plugins import discover_plugins, get_gateway_hooks, invoke_hooks

logger = logging.getLogger("mosoro.gateway")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


class RulesEngine:
    """Simple YAML-based if-then rules engine for routing decisions."""

    def __init__(self, rules_path: str = "rules.yaml"):
        self.rules: List[Dict[str, Any]] = []
        self._load_rules(rules_path)

    def _load_rules(self, path: str):
        """Load rules from YAML file."""
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            self.rules = data.get("rules", [])
            enabled_count = sum(1 for r in self.rules if r.get("enabled", True))
            logger.info(f"Loaded {len(self.rules)} rules ({enabled_count} enabled) from {path}")
        except FileNotFoundError:
            logger.warning(f"Rules file not found: {path}. Running with no rules.")
        except Exception as e:
            logger.error(f"Failed to load rules from {path}: {e}")

    def evaluate(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate all rules against a message and return matching actions.

        Args:
            message: Parsed MosoroMessage dict.

        Returns:
            List of action dicts from matching rules.
        """
        actions = []
        msg_type = message.get("type", "")
        msg_vendor = message.get("vendor", "")
        payload = message.get("payload", {})

        for rule in self.rules:
            if not rule.get("enabled", True):
                continue

            trigger = rule.get("trigger", {})

            # Check message type
            if trigger.get("type") and trigger["type"] != msg_type:
                continue

            # Check vendor
            if trigger.get("vendor") and trigger["vendor"] != msg_vendor:
                continue

            # Check conditions
            conditions = trigger.get("conditions", {})
            if not self._check_conditions(conditions, payload):
                continue

            # Rule matched
            action = rule.get("action", {})
            action["_rule_name"] = rule.get("name", "unnamed")
            action["_source_message"] = message
            actions.append(action)
            logger.info(f"Rule matched: {rule.get('name')} for robot {message.get('robot_id')}")

        return actions

    def _check_conditions(self, conditions: Dict[str, Any], payload: Dict[str, Any]) -> bool:
        """Check if all conditions match the payload."""
        for key, expected in conditions.items():
            if key == "battery_below":
                battery = payload.get("battery")
                if battery is None or battery >= expected:
                    return False
            elif key == "event_type":
                if payload.get("event_type") != expected:
                    return False
            elif key == "task_type":
                task = payload.get("current_task", {})
                if task.get("task_type") != expected:
                    return False
            else:
                if payload.get(key) != expected:
                    return False
        return True


class MosoroGateway:
    """Central Mosoro Gateway — MQTT subscriber + rules engine + state store."""

    def __init__(self, rules_path: str = "rules.yaml"):
        # MQTT Configuration
        self.mqtt_broker = os.environ.get("MQTT_BROKER_HOST", "localhost")
        self.mqtt_port = int(os.environ.get("MQTT_BROKER_PORT", "8883"))
        self.use_tls = os.environ.get("MQTT_USE_TLS", "true").lower() in ("true", "1", "yes")

        # State store and rules engine
        self.state = FleetStateStore()
        self.rules = RulesEngine(rules_path)

        # MQTT Client
        self.client = mqtt.Client(client_id="mosoro-gateway")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        # Configure TLS if enabled
        if self.use_tls:
            self._configure_tls()

        # Graceful shutdown
        self.running = True
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

        # Discover plugins and extract gateway hooks
        plugins = discover_plugins()
        self.gateway_hooks = get_gateway_hooks(plugins)
        logger.info("Gateway loaded %d plugin hook event(s).", len(self.gateway_hooks))

        # Metrics stubs (future: Prometheus)
        self._messages_received = 0
        self._commands_sent = 0
        self._rules_matched = 0

    def _configure_tls(self):
        """Configure TLS for MQTT connection."""
        try:
            from security.mqtt_tls import create_ssl_context

            ca_cert = os.environ.get("MQTT_CA_CERT", "/run/secrets/mqtt_ca_cert")
            client_cert = os.environ.get("MQTT_CLIENT_CERT")
            client_key = os.environ.get("MQTT_CLIENT_KEY")

            ssl_context = create_ssl_context(ca_cert, client_cert, client_key)
            self.client.tls_set_context(ssl_context)
            logger.info("Gateway TLS configured via security module")
        except ImportError:
            logger.warning("security.mqtt_tls not available, using basic TLS")
            import ssl

            ca_cert = os.environ.get("MQTT_CA_CERT", "/run/secrets/mqtt_ca_cert")
            try:
                self.client.tls_set(ca_certs=ca_cert, tls_version=ssl.PROTOCOL_TLS_CLIENT)
            except FileNotFoundError as e:
                logger.warning("TLS cert not found: %s. Falling back to non-TLS.", e)
                self.use_tls = False
        except FileNotFoundError as e:
            logger.warning("TLS cert not found: %s. Falling back to non-TLS.", e)
            self.use_tls = False

    def _on_connect(self, client, userdata, flags, rc):
        """Called when connected to MQTT broker."""
        if rc == 0:
            logger.info(f"Gateway connected to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")

            # Subscribe to all agent topics
            subscriptions = [
                ("mosoro/v1/agents/+/status", 1),
                ("mosoro/v1/agents/+/events", 1),
                ("mosoro/v1/agents/+/birth", 1),
            ]
            for topic, qos in subscriptions:
                client.subscribe(topic, qos)
                logger.info(f"Subscribed to: {topic}")
        else:
            logger.error(f"Failed to connect to MQTT, return code: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Called when disconnected from MQTT broker."""
        logger.warning(f"Gateway disconnected from MQTT (rc={rc})")

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages."""
        try:
            payload = json.loads(msg.payload.decode())
            self._messages_received += 1

            # Extract robot_id from topic: mosoro/v1/agents/{robot_id}/...
            topic_parts = msg.topic.split("/")
            if len(topic_parts) >= 4:
                robot_id = topic_parts[3]
                msg_type = topic_parts[4] if len(topic_parts) > 4 else "unknown"
            else:
                logger.warning(f"Unexpected topic format: {msg.topic}")
                return

            logger.debug(f"Received {msg_type} from {robot_id}")

            # Process asynchronously
            asyncio.run_coroutine_threadsafe(
                self._process_message(robot_id, msg_type, payload, msg.topic),
                self._loop,
            )

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON on {msg.topic}: {e}")
        except Exception as e:
            logger.error(f"Error processing message on {msg.topic}: {e}")

    async def _process_message(
        self, robot_id: str, msg_type: str, payload: Dict[str, Any], topic: str
    ):
        """Process a received message: update state and evaluate rules."""
        # Invoke on_message_received plugin hooks
        try:
            invoke_hooks(
                self.gateway_hooks,
                "on_message_received",
                topic=topic,
                payload=payload,
            )
        except Exception:
            logger.exception("Unexpected error invoking plugin hooks.")

        vendor = payload.get("vendor", "unknown")

        # Update fleet state
        if msg_type in ("status", "birth"):
            await self.state.update_robot(robot_id, vendor, payload)

        # Store events
        if msg_type == "events":
            await self.state.add_event(
                {
                    "robot_id": robot_id,
                    "vendor": vendor,
                    "topic": topic,
                    "payload": payload,
                }
            )

        # Handle birth messages
        if msg_type == "birth":
            logger.info(f"Robot {robot_id} ({vendor}) came online")

        # Evaluate rules
        actions = self.rules.evaluate(payload)
        for action in actions:
            self._rules_matched += 1

            # Invoke on_rule_matched plugin hooks
            try:
                invoke_hooks(
                    self.gateway_hooks,
                    "on_rule_matched",
                    rule_name=action.get("_rule_name", "unknown"),
                    trigger_message=payload,
                    action=action,
                )
            except Exception:
                logger.exception("Unexpected error invoking plugin hooks.")

            await self._execute_action(action, robot_id)

    async def _execute_action(self, action: Dict[str, Any], source_robot_id: str):
        """Execute a rule action (send command, publish traffic, log)."""
        action_type = action.get("type", "")
        rule_name = action.get("_rule_name", "unknown")
        source_msg = action.get("_source_message", {})

        if action_type == "send_command":
            await self._execute_send_command(action, source_robot_id, source_msg)

        elif action_type == "publish_traffic":
            topic = action.get("topic", "mosoro/v1/traffic/update")
            traffic_payload = action.get("payload", {})
            traffic_payload["source_robot_id"] = source_robot_id
            self.client.publish(topic, json.dumps(traffic_payload), qos=1)
            logger.info(f"Published traffic update on {topic} (rule: {rule_name})")

        elif action_type == "log":
            level = action.get("level", "info")
            message = action.get("message", "Rule triggered")
            # Simple template substitution
            message = message.replace("{robot_id}", source_robot_id)
            message = message.replace(
                "{errors}", str(source_msg.get("payload", {}).get("errors", []))
            )
            getattr(logger, level, logger.info)(f"[Rule: {rule_name}] {message}")

        else:
            logger.warning(f"Unknown action type: {action_type} in rule {rule_name}")

    async def _execute_send_command(
        self, action: Dict[str, Any], source_robot_id: str, source_msg: Dict[str, Any]
    ):
        """Execute a send_command action."""
        target_config = action.get("target", {})
        command = action.get("command", {})
        strategy = target_config.get("strategy", "specific")

        target_robot = None

        if strategy == "self":
            target_robot = await self.state.get_robot(source_robot_id)

        elif strategy == "nearest_idle":
            # Get source position
            source_state = await self.state.get_robot(source_robot_id)
            if source_state and source_state.position:
                pos = source_state.position
                target_robot = await self.state.get_nearest_robot(
                    x=pos.get("x", 0),
                    y=pos.get("y", 0),
                    vendor=target_config.get("vendor"),
                    status=target_config.get("status", "idle"),
                )

        elif strategy == "specific":
            target_id = target_config.get("robot_id")
            if target_id:
                target_robot = await self.state.get_robot(target_id)

        if target_robot:
            # Build command message
            cmd_payload = {
                "header": {"message_id": str(uuid4()), "version": "1.0"},
                "robot_id": target_robot.robot_id,
                "vendor": target_robot.vendor,
                "type": "command",
                "payload": command,
            }

            # If use_source_position, inject source robot's position
            if command.get("parameters", {}).get("use_source_position"):
                source_state = await self.state.get_robot(source_robot_id)
                if source_state and source_state.position:
                    cmd_payload["payload"]["position"] = source_state.position

            topic = f"mosoro/v1/agents/{target_robot.robot_id}/commands"
            self.client.publish(topic, json.dumps(cmd_payload), qos=1)
            self._commands_sent += 1
            logger.info(
                f"Sent command '{command.get('action')}' to {target_robot.robot_id} "
                f"(rule: {action.get('_rule_name')})"
            )

            # Invoke on_command_sent plugin hooks
            try:
                invoke_hooks(
                    self.gateway_hooks,
                    "on_command_sent",
                    robot_id=target_robot.robot_id,
                    command=cmd_payload,
                )
            except Exception:
                logger.exception("Unexpected error invoking plugin hooks.")
        else:
            logger.warning(
                f"No target robot found for strategy '{strategy}' "
                f"(rule: {action.get('_rule_name')})"
            )

    async def _cleanup_loop(self):
        """Periodically clean up expired state entries."""
        while self.running:
            await asyncio.sleep(30)
            expired = await self.state.cleanup_expired()
            if expired > 0:
                logger.info(f"Cleaned up {expired} expired robot states")

    async def _metrics_loop(self):
        """Periodically log metrics (future: expose via Prometheus)."""
        while self.running:
            await asyncio.sleep(60)
            summary = await self.state.get_fleet_summary()
            logger.info(
                f"Metrics: msgs={self._messages_received}, "
                f"cmds={self._commands_sent}, "
                f"rules_matched={self._rules_matched}, "
                f"fleet={summary}"
            )

    def _shutdown(self, *args):
        """Graceful shutdown."""
        logger.info("Shutting down Mosoro gateway...")
        self.running = False
        self.client.disconnect()

    def run(self):
        """Start the gateway."""
        logger.info("Starting Mosoro Central Gateway...")

        # Connect to MQTT
        self.client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
        self.client.loop_start()

        # Run async event loop
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(
                asyncio.gather(
                    self._cleanup_loop(),
                    self._metrics_loop(),
                )
            )
        except KeyboardInterrupt:
            pass
        finally:
            self.client.loop_stop()
            self._loop.close()
            logger.info("Mosoro gateway stopped.")


if __name__ == "__main__":
    rules_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("RULES_PATH", "rules.yaml")
    gateway = MosoroGateway(rules_path=rules_path)
    gateway.run()
