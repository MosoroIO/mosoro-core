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
Includes in-memory notification store, offline detection, and outbound webhook dispatch.
"""

import json
import logging
import os
import threading
import time
import urllib.request
import urllib.error
from typing import Any, Callable, Dict, List, Optional

import paho.mqtt.client as mqtt

logger = logging.getLogger("mosoro.api.mqtt_subscriber")

# Offline threshold: robot is considered offline if no update for this many seconds
OFFLINE_THRESHOLD_SECONDS = int(os.environ.get("ROBOT_OFFLINE_THRESHOLD", "30"))

# Notification event types that will fire toasts and webhook
ALERTABLE_STATUSES = {"error"}


class MQTTFleetSubscriber:
    """
    Background MQTT subscriber that maintains fleet state for the API.

    Subscribes to agent status/events topics and updates an in-memory
    state dict that the API endpoints read from.

    Also maintains an in-memory notification log and dispatches webhook
    calls when alertable events occur (robot offline, error status).
    """

    def __init__(self):
        self.mqtt_broker = os.environ.get("MQTT_BROKER_HOST", "localhost")
        self.mqtt_port = int(os.environ.get("MQTT_BROKER_PORT", "8883"))
        self.use_tls = os.environ.get("MQTT_USE_TLS", "true").lower() in ("true", "1", "yes")

        # Fleet state (shared with API endpoints)
        self._robots: Dict[str, Dict[str, Any]] = {}
        self._events: List[Dict[str, Any]] = []
        self._max_events = 500

        # Notification store (in-memory, cleared on restart)
        self._notifications: List[Dict[str, Any]] = []
        self._max_notifications = 200

        # Track previous robot statuses to detect transitions
        self._prev_status: Dict[str, Optional[str]] = {}
        # Track which robots have been flagged as offline to avoid repeat alerts
        self._flagged_offline: set = set()

        self._connected = False
        self._start_time = time.time()
        self._offline_check_thread: Optional[threading.Thread] = None
        self._running = False

        # WebSocket broadcast callbacks
        self._ws_callbacks: List[Callable] = []

        # Webhook config (optional — set NOTIFY_WEBHOOK_URL in .env)
        self._webhook_url: Optional[str] = os.environ.get("NOTIFY_WEBHOOK_URL", "").strip() or None
        self._webhook_events: set = set(
            os.environ.get("NOTIFY_EVENTS", "offline,error,task_failed").split(",")
        )

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
        except (ValueError, OSError) as e:
            # TLS 1.3 minimum_version enforcement may fail on older OpenSSL builds
            # (e.g. macOS system Python). Safe to fall back in dev; Docker prod has
            # a current OpenSSL.
            logger.warning(f"TLS configuration not supported by this OpenSSL build: {e}. Falling back to non-TLS.")
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
                    self._check_status_transition(robot_id)

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
        # When a robot sends a status update, it is back online — clear offline flag
        self._flagged_offline.discard(robot_id)

        self._robots[robot_id] = {
            "robot_id": robot_id,
            "vendor": data.get("vendor", "unknown"),
            "data": data,
            "last_updated": time.time(),
        }

    def _check_status_transition(self, robot_id: str):
        """Detect status transitions and fire notifications for alertable states."""
        state = self._robots.get(robot_id)
        if not state:
            return

        payload = state.get("data", {}).get("payload", {})
        new_status = payload.get("status")
        prev_status = self._prev_status.get(robot_id)

        # Only alert on transition INTO an alertable status (not on every message)
        if new_status != prev_status and new_status in ALERTABLE_STATUSES:
            notification = self._build_notification(
                robot_id=robot_id,
                vendor=state.get("vendor", "unknown"),
                event_type=new_status,
                message=f"Robot {robot_id} entered {new_status} state",
            )
            self._add_notification(notification)
            self._dispatch_webhook(notification)

        self._prev_status[robot_id] = new_status

    def _check_offline_robots(self):
        """Background thread: detect robots that have gone offline (no heartbeat)."""
        while self._running:
            now = time.time()
            for robot_id, state in list(self._robots.items()):
                last_updated = state.get("last_updated", 0)
                if (
                    now - last_updated > OFFLINE_THRESHOLD_SECONDS
                    and robot_id not in self._flagged_offline
                ):
                    self._flagged_offline.add(robot_id)
                    notification = self._build_notification(
                        robot_id=robot_id,
                        vendor=state.get("vendor", "unknown"),
                        event_type="offline",
                        message=f"Robot {robot_id} went offline (no update for >{OFFLINE_THRESHOLD_SECONDS}s)",
                    )
                    self._add_notification(notification)
                    self._dispatch_webhook(notification)

                    # Push an offline robot_update to WebSocket clients
                    response = self._state_to_response(state)
                    response["is_online"] = False
                    response["status"] = "offline"
                    self._notify_ws_clients({"type": "robot_update", "data": response})
                    # Also push as an alert event for the notifications panel
                    self._notify_ws_clients({"type": "notification", "data": notification})

            time.sleep(10)  # Check every 10 seconds

    @staticmethod
    def _build_notification(
        robot_id: str, vendor: str, event_type: str, message: str
    ) -> Dict[str, Any]:
        """Build a notification record."""
        return {
            "id": f"{robot_id}:{event_type}:{int(time.time())}",
            "robot_id": robot_id,
            "vendor": vendor,
            "event_type": event_type,
            "message": message,
            "timestamp": time.time(),
            "read": False,
        }

    def _add_notification(self, notification: Dict[str, Any]):
        """Add a notification to the in-memory log and broadcast to WebSocket clients."""
        self._notifications.append(notification)
        if len(self._notifications) > self._max_notifications:
            self._notifications = self._notifications[-self._max_notifications :]

        logger.info(f"Notification: [{notification['event_type']}] {notification['message']}")

        # Broadcast to connected dashboard clients
        self._notify_ws_clients({"type": "notification", "data": notification})

    def _dispatch_webhook(self, notification: Dict[str, Any]):
        """POST the notification to the configured webhook URL (fire-and-forget)."""
        if not self._webhook_url:
            return
        if notification["event_type"] not in self._webhook_events:
            return

        webhook_url: str = self._webhook_url  # narrowed; guard above ensures non-None

        def _post():
            try:
                body = json.dumps(notification).encode()
                req = urllib.request.Request(
                    webhook_url,
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    logger.info(f"Webhook delivered: {resp.status} for {notification['event_type']}")
            except urllib.error.URLError as e:
                logger.warning(f"Webhook delivery failed: {e}")
            except Exception as e:
                logger.warning(f"Webhook error: {e}")

        threading.Thread(target=_post, daemon=True).start()

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

    def get_notifications(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent notifications (newest first)."""
        return list(reversed(self._notifications[-limit:]))

    def mark_notifications_read(self):
        """Mark all notifications as read."""
        for n in self._notifications:
            n["read"] = True

    def get_unread_notification_count(self) -> int:
        """Get the count of unread notifications."""
        return sum(1 for n in self._notifications if not n.get("read", False))

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
        """Start the MQTT subscriber (blocking connect + loop_start) and offline checker."""
        try:
            self.client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
            self.client.loop_start()
            logger.info("MQTT fleet subscriber started")
        except Exception as e:
            logger.error(f"Failed to start MQTT subscriber: {e}")

        # Start offline detection background thread
        self._running = True
        self._offline_check_thread = threading.Thread(
            target=self._check_offline_robots, daemon=True, name="mosoro-offline-check"
        )
        self._offline_check_thread.start()
        logger.info(f"Offline detection started (threshold: {OFFLINE_THRESHOLD_SECONDS}s)")

        if self._webhook_url:
            logger.info(f"Webhook notifications enabled → {self._webhook_url} for events: {self._webhook_events}")
        else:
            logger.info("Webhook notifications disabled (set NOTIFY_WEBHOOK_URL to enable)")

    def stop(self):
        """Stop the MQTT subscriber and offline checker."""
        self._running = False
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT fleet subscriber stopped")
