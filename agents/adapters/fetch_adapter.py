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
Mosoro Adapter for Fetch Robotics (Zebra) AMRs
================================================

Fetch Robotics (now part of Zebra Technologies) uses a REST API for
fleet management. Their FetchCore platform provides endpoints for
robot status, task assignment, and navigation.

Fetch REST API reference:
    GET  /api/v1/robots/{id}         - Robot status
    GET  /api/v1/robots/{id}/state   - Detailed state
    POST /api/v1/tasks               - Create a task
    PUT  /api/v1/robots/{id}/action  - Send action (pause, resume, etc.)
"""

import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp

from agents.adapters.base_adapter import BaseMosoroAdapter
from mosoro_core.models import MosoroMessage


class FetchAdapter(BaseMosoroAdapter):
    """Adapter for Fetch Robotics (Zebra) cart/tote transport AMRs."""

    vendor_name = "fetch"

    def __init__(self, robot_id: str, config: Dict[str, Any]):
        super().__init__(robot_id, config)
        self.api_base = config.get("api_base_url", "http://localhost:8080")
        self.api_key = config.get("api_key")
        self.api_version = config.get("api_version", "v1")
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> bool:
        """Initialize HTTP session for Fetch/FetchCore API."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self.session = aiohttp.ClientSession(headers=headers)
        self.connected = True
        self.logger.info(f"Fetch adapter {self.robot_id} connected to {self.api_base}")
        return True

    async def disconnect(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
        self.connected = False
        self.logger.info(f"Fetch adapter {self.robot_id} disconnected")

    async def _fetch_robot_status(self) -> Dict[str, Any]:
        """Fetch status from Fetch/FetchCore REST API and normalize it."""
        if not self.session:
            await self.connect()

        try:
            # Fetch robot state endpoint
            async with self.session.get(
                f"{self.api_base}/api/{self.api_version}/robots/{self.robot_id}/state"
            ) as resp:
                if resp.status != 200:
                    self.logger.error(f"Fetch API returned {resp.status}")
                    raise Exception(f"HTTP {resp.status}")

                data = await resp.json()

                # Normalize Fetch-specific fields to Mosoro schema
                return {
                    "position": {
                        "x": data.get("pose", {}).get("x", 0.0),
                        "y": data.get("pose", {}).get("y", 0.0),
                        "theta": data.get("pose", {}).get("theta", 0.0),
                        "map_id": data.get("map_name"),
                    },
                    "battery": data.get("battery_level", 0.0),
                    "status": self._map_fetch_status(data.get("robot_state", "unknown")),
                    "current_task": {
                        "task_id": data.get("current_task_id"),
                        "task_type": data.get("task_type", "unknown"),
                        "progress": data.get("task_progress", 0.0),
                    } if data.get("current_task_id") else None,
                    "health": self._assess_health(data),
                    "vendor_specific": {
                        "fetch_state": data.get("robot_state"),
                        "localization_score": data.get("localization_score"),
                        "wifi_signal": data.get("wifi_signal_strength"),
                        "load_detected": data.get("load_detected", False),
                        "cart_attached": data.get("cart_attached", False),
                        "speed": data.get("current_speed", 0.0),
                        "firmware_version": data.get("firmware_version"),
                    },
                }
        except Exception as e:
            self.logger.error(f"Failed to fetch Fetch Robotics status: {e}")
            raise

    def _map_fetch_status(self, fetch_state: str) -> str:
        """
        Map Fetch Robotics states to Mosoro standard status.

        Fetch states:
            IDLE        - Robot is idle, waiting for tasks
            NAVIGATING  - Robot is moving to a destination
            EXECUTING   - Robot is executing a task action
            DOCKING     - Robot is docking to a charger
            CHARGING    - Robot is charging
            ERROR       - Robot has an error
            PAUSED      - Robot is paused
            MANUAL      - Robot is in manual control mode
        """
        mapping = {
            "IDLE": "idle",
            "NAVIGATING": "moving",
            "EXECUTING": "working",
            "DOCKING": "moving",
            "CHARGING": "charging",
            "ERROR": "error",
            "PAUSED": "idle",
            "MANUAL": "working",
            "OFFLINE": "offline",
        }
        return mapping.get(fetch_state.upper(), "idle")

    def _assess_health(self, data: Dict[str, Any]) -> str:
        """Assess robot health from Fetch status data."""
        state = data.get("robot_state", "").upper()
        if state == "ERROR":
            return "error"

        # Check localization quality
        loc_score = data.get("localization_score", 1.0)
        if loc_score is not None and loc_score < 0.5:
            return "warning"

        # Check for reported faults
        faults = data.get("faults", [])
        if faults:
            return "warning"

        return "good"

    async def send_command(self, command: Dict[str, Any]) -> bool:
        """Send command to Fetch robot via REST API."""
        if not self.session:
            await self.connect()

        action = command.get("action")
        self.logger.info(f"Sending {action} command to Fetch robot {self.robot_id}")

        try:
            if action == "move_to":
                # Fetch uses task-based navigation
                payload = {
                    "robot_id": self.robot_id,
                    "task_type": "navigate",
                    "destination": {
                        "x": command["position"]["x"],
                        "y": command["position"]["y"],
                        "theta": command["position"].get("theta", 0.0),
                    },
                }
                async with self.session.post(
                    f"{self.api_base}/api/{self.api_version}/tasks",
                    json=payload,
                ) as resp:
                    return resp.status in (200, 201, 202)

            elif action == "pause":
                async with self.session.put(
                    f"{self.api_base}/api/{self.api_version}/robots/{self.robot_id}/action",
                    json={"action": "pause"},
                ) as resp:
                    return resp.status == 200

            elif action == "resume":
                async with self.session.put(
                    f"{self.api_base}/api/{self.api_version}/robots/{self.robot_id}/action",
                    json={"action": "resume"},
                ) as resp:
                    return resp.status == 200

            elif action == "dock":
                # Send to charging dock
                async with self.session.put(
                    f"{self.api_base}/api/{self.api_version}/robots/{self.robot_id}/action",
                    json={"action": "dock"},
                ) as resp:
                    return resp.status == 200

            elif action == "undock":
                async with self.session.put(
                    f"{self.api_base}/api/{self.api_version}/robots/{self.robot_id}/action",
                    json={"action": "undock"},
                ) as resp:
                    return resp.status == 200

            self.logger.warning(f"Unknown command action: {action}")
            return False

        except Exception as e:
            self.logger.error(f"Failed to send command to Fetch: {e}")
            return False
