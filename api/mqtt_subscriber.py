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
Mosoro API MQTT Subscriber
===========================

Background MQTT subscriber that feeds fleet state into the API layer.
Runs as an asyncio background task alongside the FastAPI server.
"""

import json
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional

import paho.mqtt.client as mqtt

logger = logging.getLogger("mosoro.api.mqtt_subscriber")


class MQTTFleetSubscriber:
    """
    Background MQTT subscriber that maintains fleet state for the API.

    Subscribes to agent status/events topics and updates an in-memory
    state dict that the API endpoints read from.
    """

    def __init__(self):
        self.mqtt_broker = os.environ.get("MQTT_BROKER_HOST", "localhost")
        self.mqtt_port = int(os.environ.get("MQTT_BROKER_PORT", "8883"))
        self.use_tls = os.environ.get("MQTT_USE_TLS", "true").lower() in ("true", "1", "yes")

        # Fleet state (shared with API endpoints)
        self._robots: Dict[str, Dict[str, Any]] = {}
        self._events: List[Dict[str, Any]] = []
        self._max_events = 500
        self._connected = False
        self._start_time = time.time()

        # WebSocket broadcast callbacks
        self._ws_callbacks: List[Callable] = []

        # MQTT client
        self.client = mqtt.Client(client_id="mosoro-api-subscriber")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        # Configure TLS
        if self.use_tls:
            self._configure_tls()

    def _configure_tls(self):
        """Configure TLS for MQTT connection."""
        try:
            from security.mqtt_tls import create_ssl_context

            ca_cert = os.environ.get("MQTT_CA_CERT", "/run/secrets/mqtt_ca_cert")
            client_cert = os.environ.get("MQTT_CLIENT_CERT")
            client_key = os.environ.get("MQTT_CLIENT_KEY")

            ssl_context = create_ssl_context(ca_cert, client_cert, client_key)
            self.client.tls_set_context(ssl_context)
            logger.info("API MQTT subscriber TLS configured")
        except ImportError:
            logger.warning("security.mqtt_tls not available")
        except FileNotFoundError as e:
            logger.warning(f"TLS cert not found: {e}. Falling back to non-TLS.")
            self.use_tls = False

    def _on_connect(self, client, userdata, flags, rc):
        """Called when connected to MQTT broker."""
        if rc == 0:
            self._connected = True
            logger.info(f"API subscriber connected to MQTT at {self.mqtt_broker}:{self.mqtt_port}")

            # Subscribe to fleet topics
            topics = [
                ("mosoro/v1/agents/+/status", 1),
                ("mosoro/v1/agents/+/events", 1),
                ("mosoro/v1/agents/+/birth", 1),
                ("mosoro/v1/traffic/#", 0),
            ]
            for topic, qos in topics:
                client.subscribe(topic, qos)
                logger.info(f"API subscribed to: {topic}")
        else:
            logger.error(f"API subscriber failed to connect, rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Called when disconnected from MQTT broker."""
        self._connected = False
        logger.warning(f"API subscriber disconnected from MQTT (rc={rc})")

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages."""
        try:
            payload = json.loads(msg.payload.decode())
            topic_parts = msg.topic.split("/")

            if len(topic_parts) >= 5 and topic_parts[2] == "agents":
                robot_id = topic_parts[3]
                msg_type = topic_parts[4]

                if msg_type in ("status", "birth"):
                    self._update_robot_state(robot_id, payload)
                    # Notify WebSocket clients with a properly structured robot_update
                    state = self._robots.get(robot_id, {})
                    self._notify_ws_clients(
                        {
                            "type": "robot_update",
                            "data": self._state_to_response(state),
                        }
                    )
                elif msg_type == "events":
                    self._add_event(robot_id, payload, msg.topic)
                    self._notify_ws_clients(
                        {
                            "type": "event",
                            "data": {
                                "robot_id": robot_id,
                                "vendor": payload.get("vendor", "unknown"),
                                "topic": msg.topic,
                                "payload": payload,
                                "received_at": time.time(),
                            },
                        }
                    )

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON on {msg.topic}: {e}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _update_robot_state(self, robot_id: str, data: Dict[str, Any]):
        """Update the in-memory robot state."""
        self._robots[robot_id] = {
            "robot_id": robot_id,
            "vendor": data.get("vendor", "unknown"),
            "data": data,
            "last_updated": time.time(),
        }

    @staticmethod
    def _state_to_response(state: Dict[str, Any]) -> Dict[str, Any]:
        """Convert internal robot state dict to RobotStatusResponse-compatible dict."""
        inner = state.get("data", {})
        payload = inner.get("payload", {})
        return {
            "robot_id": state.get("robot_id", "unknown"),
            "vendor": state.get("vendor", "unknown"),
            "status": payload.get("status"),
            "position": payload.get("position"),
            "battery": payload.get("battery"),
            "health": payload.get("health"),
            "current_task": payload.get("current_task"),
            "last_updated": state.get("last_updated", 0),
            "is_online": True,
        }

    def _add_event(self, robot_id: str, data: Dict[str, Any], topic: str):
        """Add an event to the event log."""
        self._events.append(
            {
                "robot_id": robot_id,
                "vendor": data.get("vendor", "unknown"),
                "topic": topic,
                "payload": data,
                "received_at": time.time(),
            }
        )
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events :]

    def _notify_ws_clients(self, message: Dict[str, Any]):
        """Notify all registered WebSocket callbacks."""
        for callback in self._ws_callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"WebSocket callback error: {e}")

    # -----------------------------------------------------------------------
    # Public API (used by FastAPI endpoints)
    # -----------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        """Check if MQTT is connected."""
        return self._connected

    @property
    def uptime(self) -> float:
        """Get uptime in seconds."""
        return time.time() - self._start_time

    def get_all_robots(self) -> Dict[str, Dict[str, Any]]:
        """Get all robot states."""
        return dict(self._robots)

    def get_robot(self, robot_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific robot's state."""
        return self._robots.get(robot_id)

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events."""
        return list(self._events[-limit:])

    def get_fleet_size(self) -> int:
        """Get the number of tracked robots."""
        return len(self._robots)

    def register_ws_callback(self, callback: Callable):
        """Register a WebSocket broadcast callback."""
        self._ws_callbacks.append(callback)

    def unregister_ws_callback(self, callback: Callable):
        """Unregister a WebSocket broadcast callback."""
        self._ws_callbacks = [cb for cb in self._ws_callbacks if cb != callback]

    def publish_command(self, robot_id: str, command: Dict[str, Any]) -> bool:
        """Publish a command to a robot via MQTT."""
        if not self._connected:
            logger.error("Cannot publish command: MQTT not connected")
            return False

        topic = f"mosoro/v1/agents/{robot_id}/commands"
        try:
            result = self.client.publish(topic, json.dumps(command), qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published command to {topic}")
                return True
            else:
                logger.error(f"Failed to publish command to {topic}: rc={result.rc}")
                return False
        except Exception as e:
            logger.error(f"Error publishing command: {e}")
            return False

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    def start(self):
        """Start the MQTT subscriber (blocking connect + loop_start)."""
        try:
            self.client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
            self.client.loop_start()
            logger.info("MQTT fleet subscriber started")
        except Exception as e:
            logger.error(f"Failed to start MQTT subscriber: {e}")

    def stop(self):
        """Stop the MQTT subscriber."""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT fleet subscriber stopped")
