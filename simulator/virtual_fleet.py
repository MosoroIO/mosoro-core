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
Mosoro Virtual Fleet Simulator
===============================

Simulates 3 virtual robots publishing MosoroMessage-compliant JSON to MQTT.
Designed for zero-configuration demo mode — all defaults are baked in.

Robots:
    - locus-001   (Locus Robotics AMR)
    - stretch-001 (Boston Dynamics Stretch)
    - mir-001     (MiR Mobile Industrial)

Usage:
    python -m simulator.virtual_fleet
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

import paho.mqtt.client as mqtt

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("mosoro.simulator")

# ---------------------------------------------------------------------------
# Configuration — all defaults baked in, overridable via env vars
# ---------------------------------------------------------------------------

MQTT_BROKER_HOST: str = os.environ.get("MQTT_BROKER_HOST", "mosquitto")
MQTT_BROKER_PORT: int = int(os.environ.get("MQTT_BROKER_PORT", "1883"))
PUBLISH_INTERVAL_MIN: float = float(os.environ.get("SIM_INTERVAL_MIN", "3.0"))
PUBLISH_INTERVAL_MAX: float = float(os.environ.get("SIM_INTERVAL_MAX", "5.0"))

# Warehouse grid boundaries (metres)
GRID_X_MIN: float = 0.0
GRID_X_MAX: float = 50.0
GRID_Y_MIN: float = 0.0
GRID_Y_MAX: float = 30.0

# Charging station location
CHARGING_X: float = 2.0
CHARGING_Y: float = 2.0

# Valid vendor literals (must match mosoro_core.models.MosoroMessage.vendor)
VendorLiteral = Literal["locus", "stretch", "seer", "geekplus", "mir", "ur", "fetch", "other"]

# Valid status literals (must match mosoro_core.models.MosoroPayload.status)
StatusLiteral = Literal["idle", "moving", "working", "charging", "error", "offline"]

# Valid message type literals (must match mosoro_core.models.MosoroMessage.type)
TypeLiteral = Literal["status", "event", "command", "traffic_update", "birth", "error"]

# ---------------------------------------------------------------------------
# Task templates
# ---------------------------------------------------------------------------

TASK_TEMPLATES: List[Dict[str, str]] = [
    {"task_type": "pick", "description": "Pick item from shelf"},
    {"task_type": "place", "description": "Place item on conveyor"},
    {"task_type": "transport", "description": "Transport tote to station"},
    {"task_type": "inspection", "description": "Inspect aisle inventory"},
    {"task_type": "tote_delivery", "description": "Deliver tote to packing"},
]


# ---------------------------------------------------------------------------
# Virtual Robot State
# ---------------------------------------------------------------------------


@dataclass
class VirtualRobot:
    """Mutable state for a single simulated robot."""

    robot_id: str
    vendor: VendorLiteral
    display_name: str

    # Position
    x: float = field(default_factory=lambda: random.uniform(5.0, 45.0))
    y: float = field(default_factory=lambda: random.uniform(5.0, 25.0))
    theta: float = 0.0
    map_id: str = "warehouse-main"

    # Movement target
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    speed: float = 1.5  # metres per tick

    # Battery
    battery: float = field(default_factory=lambda: random.uniform(85.0, 100.0))
    battery_drain_rate: float = 0.15  # % per tick while active
    battery_charge_rate: float = 1.2  # % per tick while charging

    # Status
    status: StatusLiteral = "idle"
    health: str = "nominal"

    # Task
    current_task_id: Optional[str] = None
    current_task_type: Optional[str] = None
    task_progress: float = 0.0

    # Error simulation
    error_cooldown: int = 0  # ticks until next possible error

    # Tick counter for lifecycle decisions
    ticks: int = 0

    def pick_new_target(self) -> None:
        """Choose a random warehouse position to move toward."""
        self.target_x = random.uniform(GRID_X_MIN + 3.0, GRID_X_MAX - 3.0)
        self.target_y = random.uniform(GRID_Y_MIN + 3.0, GRID_Y_MAX - 3.0)

    def move_toward_target(self) -> None:
        """Move one step toward the current target."""
        if self.target_x is None or self.target_y is None:
            return
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.hypot(dx, dy)
        if dist < self.speed:
            self.x = self.target_x
            self.y = self.target_y
            self.target_x = None
            self.target_y = None
        else:
            ratio = self.speed / dist
            self.x += dx * ratio
            self.y += dy * ratio
            self.theta = math.atan2(dy, dx)

    @property
    def has_reached_target(self) -> bool:
        return self.target_x is None and self.target_y is None


# ---------------------------------------------------------------------------
# Message builders — produce dicts matching MosoroMessage JSON schema
# ---------------------------------------------------------------------------


def _build_header() -> Dict[str, Any]:
    """Build a MosoroMessage header."""
    return {
        "message_id": str(uuid4()),
        "version": "1.0",
        "correlation_id": None,
    }


def _now_iso() -> str:
    """Current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def build_status_message(robot: VirtualRobot) -> Dict[str, Any]:
    """Build a status MosoroMessage dict for the given robot."""
    payload: Dict[str, Any] = {
        "position": {
            "x": round(robot.x, 2),
            "y": round(robot.y, 2),
            "z": 0.0,
            "theta": round(robot.theta, 3),
            "map_id": robot.map_id,
        },
        "battery": round(robot.battery, 1),
        "status": robot.status,
        "health": robot.health,
        "errors": None,
        "vendor_specific": {},
    }

    if robot.current_task_id is not None:
        payload["current_task"] = {
            "task_id": robot.current_task_id,
            "task_type": robot.current_task_type,
            "progress": round(robot.task_progress, 1),
        }
    else:
        payload["current_task"] = None

    return {
        "header": _build_header(),
        "robot_id": robot.robot_id,
        "vendor": robot.vendor,
        "timestamp": _now_iso(),
        "type": "status",
        "payload": payload,
    }


def build_birth_message(robot: VirtualRobot) -> Dict[str, Any]:
    """Build a birth MosoroMessage dict for the given robot."""
    return {
        "header": _build_header(),
        "robot_id": robot.robot_id,
        "vendor": robot.vendor,
        "timestamp": _now_iso(),
        "type": "birth",
        "payload": {
            "position": {
                "x": round(robot.x, 2),
                "y": round(robot.y, 2),
                "z": 0.0,
                "theta": 0.0,
                "map_id": robot.map_id,
            },
            "battery": round(robot.battery, 1),
            "status": robot.status,
            "health": "nominal",
            "current_task": None,
            "errors": None,
            "vendor_specific": {
                "display_name": robot.display_name,
                "simulator": True,
            },
        },
    }


def build_event_message(
    robot: VirtualRobot,
    event_type: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build an event MosoroMessage dict."""
    payload: Dict[str, Any] = {
        "position": {
            "x": round(robot.x, 2),
            "y": round(robot.y, 2),
            "z": 0.0,
            "theta": round(robot.theta, 3),
            "map_id": robot.map_id,
        },
        "battery": round(robot.battery, 1),
        "status": robot.status,
        "health": robot.health,
        "current_task": None,
        "errors": None,
        "vendor_specific": {
            "event_type": event_type,
            **(details or {}),
        },
    }

    if robot.current_task_id is not None:
        payload["current_task"] = {
            "task_id": robot.current_task_id,
            "task_type": robot.current_task_type,
            "progress": round(robot.task_progress, 1),
        }

    return {
        "header": _build_header(),
        "robot_id": robot.robot_id,
        "vendor": robot.vendor,
        "timestamp": _now_iso(),
        "type": "event",
        "payload": payload,
    }


def build_error_message(
    robot: VirtualRobot,
    error_code: str,
    error_msg: str,
) -> Dict[str, Any]:
    """Build an error MosoroMessage dict."""
    return {
        "header": _build_header(),
        "robot_id": robot.robot_id,
        "vendor": robot.vendor,
        "timestamp": _now_iso(),
        "type": "error",
        "payload": {
            "position": {
                "x": round(robot.x, 2),
                "y": round(robot.y, 2),
                "z": 0.0,
                "theta": round(robot.theta, 3),
                "map_id": robot.map_id,
            },
            "battery": round(robot.battery, 1),
            "status": "error",
            "health": "degraded",
            "current_task": None,
            "errors": [
                {
                    "code": error_code,
                    "message": error_msg,
                }
            ],
            "vendor_specific": {},
        },
    }


# ---------------------------------------------------------------------------
# Simulation tick logic
# ---------------------------------------------------------------------------


def tick_robot(robot: VirtualRobot) -> List[Dict[str, Any]]:
    """
    Advance one simulation tick for a robot.

    Returns a list of MosoroMessage dicts to publish.
    """
    messages: List[Dict[str, Any]] = []
    robot.ticks += 1

    if robot.error_cooldown > 0:
        robot.error_cooldown -= 1

    # --- State machine ---

    if robot.status == "charging":
        robot.battery = min(100.0, robot.battery + robot.battery_charge_rate)
        if robot.battery >= 95.0:
            robot.status = "idle"
            robot.health = "nominal"
            messages.append(
                build_event_message(
                    robot, "charging_complete", {"battery": round(robot.battery, 1)}
                )
            )
            logger.info("%s finished charging (battery=%.1f%%)", robot.robot_id, robot.battery)

    elif robot.status == "error":
        # Recover from error after a few ticks
        if robot.ticks % 8 == 0:
            robot.status = "idle"
            robot.health = "nominal"
            messages.append(build_event_message(robot, "error_cleared"))
            logger.info("%s recovered from error", robot.robot_id)

    elif robot.status == "idle":
        # Decide what to do next
        if robot.battery < 20.0:
            # Go charge
            robot.status = "moving"
            robot.target_x = CHARGING_X
            robot.target_y = CHARGING_Y
            robot.health = "low_battery"
            logger.info("%s heading to charger (battery=%.1f%%)", robot.robot_id, robot.battery)
        elif random.random() < 0.4:
            # Start a new task
            template = random.choice(TASK_TEMPLATES)
            robot.current_task_id = f"task-{uuid4().hex[:8]}"
            robot.current_task_type = template["task_type"]
            robot.task_progress = 0.0
            robot.status = "moving"
            robot.pick_new_target()
            messages.append(
                build_event_message(
                    robot,
                    "task_assigned",
                    {
                        "task_id": robot.current_task_id,
                        "task_type": robot.current_task_type,
                    },
                )
            )
            logger.info(
                "%s assigned task %s (%s)",
                robot.robot_id,
                robot.current_task_id,
                robot.current_task_type,
            )

    elif robot.status == "moving":
        robot.move_toward_target()
        robot.battery = max(0.0, robot.battery - robot.battery_drain_rate)

        if robot.has_reached_target:
            # Arrived — check if we were heading to charger
            if robot.battery < 25.0 and robot.current_task_id is None:
                robot.status = "charging"
                logger.info("%s started charging", robot.robot_id)
            elif robot.current_task_id is not None:
                robot.status = "working"
                logger.debug("%s arrived at task location, now working", robot.robot_id)
            else:
                robot.status = "idle"

    elif robot.status == "working":
        robot.battery = max(0.0, robot.battery - robot.battery_drain_rate * 0.5)
        robot.task_progress = min(100.0, robot.task_progress + random.uniform(8.0, 20.0))

        if robot.task_progress >= 100.0:
            # Task complete
            robot.task_progress = 100.0
            completed_task_id = robot.current_task_id
            completed_task_type = robot.current_task_type
            messages.append(
                build_event_message(
                    robot,
                    "task_complete",
                    {
                        "task_id": completed_task_id,
                        "task_type": completed_task_type,
                    },
                )
            )
            logger.info(
                "%s completed task %s (%s)",
                robot.robot_id,
                completed_task_id,
                completed_task_type,
            )
            robot.current_task_id = None
            robot.current_task_type = None
            robot.task_progress = 0.0
            robot.status = "idle"

    # --- Occasional error injection ---
    if (
        robot.error_cooldown == 0
        and robot.status not in ("error", "charging")
        and random.random() < 0.02  # ~2% chance per tick
    ):
        error_scenarios = [
            ("E_SENSOR", "Lidar sensor intermittent fault"),
            ("E_MOTOR", "Drive motor overcurrent detected"),
            ("E_COMM", "Temporary communication timeout"),
            ("E_NAV", "Path planning obstacle detected"),
        ]
        code, msg = random.choice(error_scenarios)
        robot.status = "error"
        robot.health = "degraded"
        robot.error_cooldown = 15  # Don't error again for 15 ticks
        # Clear any active task on error
        if robot.current_task_id is not None:
            robot.current_task_id = None
            robot.current_task_type = None
            robot.task_progress = 0.0
        messages.append(build_error_message(robot, code, msg))
        logger.warning("%s error: [%s] %s", robot.robot_id, code, msg)

    # Always emit a status message
    messages.append(build_status_message(robot))

    return messages


# ---------------------------------------------------------------------------
# MQTT publishing
# ---------------------------------------------------------------------------


def publish_messages(
    client: mqtt.Client,
    robot: VirtualRobot,
    messages: List[Dict[str, Any]],
) -> None:
    """Publish a list of MosoroMessage dicts to the appropriate MQTT topics."""
    for msg in messages:
        msg_type = msg.get("type", "status")

        if msg_type == "birth":
            topic = f"mosoro/v1/agents/{robot.robot_id}/birth"
        elif msg_type in ("event", "error"):
            topic = f"mosoro/v1/agents/{robot.robot_id}/events"
        else:
            topic = f"mosoro/v1/agents/{robot.robot_id}/status"

        payload_json = json.dumps(msg)
        result = client.publish(topic, payload_json, qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.debug("Published %s to %s", msg_type, topic)
        else:
            logger.error("Failed to publish to %s (rc=%d)", topic, result.rc)


# ---------------------------------------------------------------------------
# Fleet factory
# ---------------------------------------------------------------------------


def create_fleet() -> List[VirtualRobot]:
    """Create the default fleet of 3 virtual robots."""
    return [
        VirtualRobot(
            robot_id="locus-001",
            vendor="locus",
            display_name="Locus AMR #1",
            x=10.0,
            y=8.0,
            speed=2.0,
            battery=random.uniform(88.0, 100.0),
        ),
        VirtualRobot(
            robot_id="stretch-001",
            vendor="stretch",
            display_name="Stretch Arm #1",
            x=25.0,
            y=15.0,
            speed=1.0,
            battery=random.uniform(85.0, 97.0),
        ),
        VirtualRobot(
            robot_id="mir-001",
            vendor="mir",
            display_name="MiR 250 #1",
            x=40.0,
            y=22.0,
            speed=1.8,
            battery=random.uniform(90.0, 100.0),
        ),
    ]


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def _on_connect(client: mqtt.Client, userdata: Any, flags: Any, rc: int) -> None:
    """MQTT on_connect callback."""
    if rc == 0:
        logger.info(
            "Simulator connected to MQTT broker at %s:%d", MQTT_BROKER_HOST, MQTT_BROKER_PORT
        )
    else:
        logger.error("Simulator failed to connect to MQTT broker (rc=%d)", rc)


def _on_disconnect(client: mqtt.Client, userdata: Any, rc: int) -> None:
    """MQTT on_disconnect callback."""
    logger.warning("Simulator disconnected from MQTT broker (rc=%d)", rc)


def main() -> None:
    """Entry point — connect to MQTT and run the simulation loop."""
    logger.info("=" * 60)
    logger.info("Mosoro Virtual Fleet Simulator")
    logger.info("Broker: %s:%d", MQTT_BROKER_HOST, MQTT_BROKER_PORT)
    logger.info("Publish interval: %.1f–%.1fs", PUBLISH_INTERVAL_MIN, PUBLISH_INTERVAL_MAX)
    logger.info("=" * 60)

    # --- Graceful shutdown ---
    running = True

    def shutdown_handler(signum: int, frame: Any) -> None:
        nonlocal running
        logger.info("Received signal %d, shutting down...", signum)
        running = False

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # --- MQTT client ---
    client = mqtt.Client(client_id="mosoro-simulator")
    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect

    # Retry connection with backoff
    max_retries = 30
    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Connecting to MQTT broker (attempt %d/%d)...", attempt, max_retries)
            client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
            client.loop_start()
            break
        except (ConnectionRefusedError, OSError) as exc:
            if attempt == max_retries:
                logger.error("Failed to connect after %d attempts: %s", max_retries, exc)
                sys.exit(1)
            backoff = min(2.0 * attempt, 10.0)
            logger.warning("Connection failed (%s), retrying in %.0fs...", exc, backoff)
            time.sleep(backoff)

    # --- Create fleet ---
    fleet = create_fleet()
    logger.info("Fleet created: %s", [r.robot_id for r in fleet])

    # --- Publish birth messages ---
    time.sleep(1.0)  # Brief pause to let MQTT connection stabilise
    for robot in fleet:
        birth_msg = build_birth_message(robot)
        publish_messages(client, robot, [birth_msg])
        logger.info("Published birth for %s (%s)", robot.robot_id, robot.vendor)

    # --- Simulation loop ---
    logger.info("Simulation running — press Ctrl+C to stop")
    try:
        while running:
            for robot in fleet:
                messages = tick_robot(robot)
                publish_messages(client, robot, messages)

            interval = random.uniform(PUBLISH_INTERVAL_MIN, PUBLISH_INTERVAL_MAX)
            # Sleep in small increments so we can respond to signals quickly
            sleep_end = time.monotonic() + interval
            while running and time.monotonic() < sleep_end:
                time.sleep(0.25)

    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Stopping simulator...")
        client.loop_stop()
        client.disconnect()
        logger.info("Simulator stopped.")


if __name__ == "__main__":
    main()
