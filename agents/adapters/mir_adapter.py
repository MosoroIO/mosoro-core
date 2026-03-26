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
Mosoro Adapter for MiR (Mobile Industrial Robots) AMRs
=======================================================

MiR robots use a REST API with basic auth (username/password) for status
and commands. This adapter normalizes MiR data into the common MosoroMessage
schema.

MiR REST API reference:
    GET  /api/v2.0.0/status          - Robot status
    GET  /api/v2.0.0/robots/{id}     - Robot details
    POST /api/v2.0.0/mission_queue   - Queue a mission
    PUT  /api/v2.0.0/status          - Change state (e.g., pause/resume)
"""

import asyncio
import base64
import logging
from typing import Any, Dict, Optional

import aiohttp

from agents.adapters.base_adapter import BaseMosoroAdapter
from mosoro_core.models import MosoroMessage


class MirAdapter(BaseMosoroAdapter):
    """Adapter for MiR (Mobile Industrial Robots) collaborative AMRs."""

    vendor_name = "mir"

    def __init__(self, robot_id: str, config: Dict[str, Any]):
        super().__init__(robot_id, config)
        self.api_base = config.get("api_base_url", "http://localhost:8080")
        self.username = config.get("username", "admin")
        self.password = config.get("password", "")
        self.api_version = config.get("api_version", "v2.0.0")
        self.session: Optional[aiohttp.ClientSession] = None

    def _get_auth_header(self) -> str:
        """Generate Basic Auth header for MiR API."""
        credentials = base64.b64encode(
            f"{self.username}:{self.password}".encode()
        ).decode()
        return f"Basic {credentials}"

    async def connect(self) -> bool:
        """Initialize HTTP session for MiR API with Basic Auth."""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": self._get_auth_header(),
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        self.connected = True
        self.logger.info(f"MiR adapter {self.robot_id} connected to {self.api_base}")
        return True

    async def disconnect(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
        self.connected = False
        self.logger.info(f"MiR adapter {self.robot_id} disconnected")

    async def _fetch_robot_status(self) -> Dict[str, Any]:
        """Fetch status from MiR REST API and normalize it."""
        if not self.session:
            await self.connect()

        try:
            # MiR status endpoint
            async with self.session.get(
                f"{self.api_base}/api/{self.api_version}/status"
            ) as resp:
                if resp.status != 200:
                    self.logger.error(f"MiR API returned {resp.status}")
                    raise Exception(f"HTTP {resp.status}")

                data = await resp.json()

                # Normalize MiR-specific fields to Mosoro schema
                return {
                    "position": {
                        "x": data.get("position", {}).get("x", 0.0),
                        "y": data.get("position", {}).get("y", 0.0),
                        "theta": data.get("position", {}).get("orientation", 0.0),
                        "map_id": data.get("map_id"),
                    },
                    "battery": data.get("battery_percentage", 0.0),
                    "status": self._map_mir_status(data.get("state_id", 0)),
                    "current_task": {
                        "task_id": data.get("mission_queue_id"),
                        "task_type": data.get("mission_text", "unknown"),
                        "progress": self._calculate_progress(data),
                    } if data.get("mission_queue_id") else None,
                    "health": self._assess_health(data),
                    "vendor_specific": {
                        "mir_state_id": data.get("state_id"),
                        "mir_state_text": data.get("state_text"),
                        "velocity": {
                            "linear": data.get("velocity", {}).get("linear", 0.0),
                            "angular": data.get("velocity", {}).get("angular", 0.0),
                        },
                        "uptime": data.get("uptime"),
                        "distance_to_next_target": data.get("distance_to_next_target"),
                        "footprint": data.get("footprint"),
                    },
                }
        except Exception as e:
            self.logger.error(f"Failed to fetch MiR status: {e}")
            raise

    def _map_mir_status(self, state_id: int) -> str:
        """
        Map MiR state IDs to Mosoro standard status.

        MiR state IDs:
            1 = Starting
            2 = Shutting down
            3 = Ready (idle)
            4 = Pause
            5 = Executing (moving/working)
            6 = Aborted
            7 = Completed
            8 = Docked
            9 = Docking
            10 = Emergency stop
            11 = Manual control
            12 = Error
        """
        mapping = {
            1: "idle",       # Starting
            2: "offline",    # Shutting down
            3: "idle",       # Ready
            4: "idle",       # Pause
            5: "moving",     # Executing
            6: "error",      # Aborted
            7: "idle",       # Completed
            8: "charging",   # Docked
            9: "moving",     # Docking
            10: "error",     # Emergency stop
            11: "working",   # Manual control
            12: "error",     # Error
        }
        return mapping.get(state_id, "idle")

    def _calculate_progress(self, data: Dict[str, Any]) -> float:
        """Calculate mission progress from MiR data."""
        # MiR doesn't always provide direct progress; estimate from distance
        distance = data.get("distance_to_next_target", 0.0)
        if distance is not None and distance > 0:
            # Rough estimate — closer to target = more progress
            return max(0.0, min(100.0, 100.0 - (distance * 10)))
        return 0.0

    def _assess_health(self, data: Dict[str, Any]) -> str:
        """Assess robot health from MiR status data."""
        state_id = data.get("state_id", 0)
        if state_id in (6, 10, 12):  # Aborted, E-stop, Error
            return "error"
        errors = data.get("errors", [])
        if errors:
            return "warning"
        return "good"

    async def send_command(self, command: Dict[str, Any]) -> bool:
        """Send command to MiR robot via REST API."""
        if not self.session:
            await self.connect()

        action = command.get("action")
        self.logger.info(f"Sending {action} command to MiR robot {self.robot_id}")

        try:
            if action == "move_to":
                # MiR uses mission queue for navigation
                payload = {
                    "mission_id": command.get("mission_id"),
                    "parameters": [
                        {
                            "input_name": "x",
                            "value": command["position"]["x"],
                        },
                        {
                            "input_name": "y",
                            "value": command["position"]["y"],
                        },
                        {
                            "input_name": "orientation",
                            "value": command["position"].get("theta", 0.0),
                        },
                    ],
                }
                async with self.session.post(
                    f"{self.api_base}/api/{self.api_version}/mission_queue",
                    json=payload,
                ) as resp:
                    return resp.status in (200, 201)

            elif action == "pause":
                # MiR uses PUT /status to change state
                async with self.session.put(
                    f"{self.api_base}/api/{self.api_version}/status",
                    json={"state_id": 4},  # 4 = Pause
                ) as resp:
                    return resp.status == 200

            elif action == "resume":
                async with self.session.put(
                    f"{self.api_base}/api/{self.api_version}/status",
                    json={"state_id": 3},  # 3 = Ready
                ) as resp:
                    return resp.status == 200

            elif action == "dock":
                # Send to charging station
                async with self.session.put(
                    f"{self.api_base}/api/{self.api_version}/status",
                    json={"state_id": 9},  # 9 = Docking
                ) as resp:
                    return resp.status == 200

            self.logger.warning(f"Unknown command action: {action}")
            return False

        except Exception as e:
            self.logger.error(f"Failed to send command to MiR: {e}")
            return False
