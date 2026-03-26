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
Mosoro Base Adapter
====================

Abstract base class for all Mosoro robot adapters.

External packages (e.g., mosoro-adapters-community) should import from here::

    from mosoro_core.base_adapter import BaseMosoroAdapter

To create a new adapter:
    1. Subclass BaseMosoroAdapter
    2. Implement ``_fetch_robot_status()`` → returns dict compatible with MosoroPayload
    3. Implement ``send_command(command)`` → executes command on the physical robot
    4. Register via entry points under ``mosoro.adapters`` in your pyproject.toml

All adapters must produce normalized ``MosoroMessage`` objects.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from mosoro_core.models import MosoroMessage, MosoroPayload, Position

logger = logging.getLogger("mosoro.adapter")


class BaseMosoroAdapter(ABC):
    """
    Abstract base class for all Mosoro robot adapters.

    Every vendor-specific adapter must inherit from this class.
    """

    vendor_name: str = "unknown"

    def __init__(self, robot_id: str, config: Dict[str, Any]):
        self.robot_id = robot_id
        self.vendor = config.get("vendor", "unknown")
        self.config = config
        self.logger = logging.getLogger(f"mosoro.adapter.{self.vendor}.{robot_id}")

        # Optional: connection state
        self.connected = False

    @abstractmethod
    async def _fetch_robot_status(self) -> Dict[str, Any]:
        """
        Fetch raw status from the robot's proprietary API.

        Returns a dict that can be passed to MosoroPayload(...).
        Example keys: position, battery, status, current_task, health, vendor_specific
        """
        pass

    @abstractmethod
    async def send_command(self, command: Dict[str, Any]) -> bool:
        """
        Send a command to the physical robot.

        Args:
            command: Parsed command dict (e.g. {"action": "move_to", "position": {...}})

        Returns:
            True if command was successfully sent/accepted by the robot
        """
        pass

    async def get_normalized_status(self) -> MosoroMessage:
        """
        Public method: Fetch status and normalize it to MosoroMessage.
        This is what the main agent calls in its polling loop.
        """
        try:
            raw_status = await self._fetch_robot_status()

            payload = MosoroPayload(
                position=Position(**raw_status.get("position", {})) if raw_status.get("position") else None,
                battery=raw_status.get("battery"),
                status=raw_status.get("status"),
                current_task=raw_status.get("current_task"),
                health=raw_status.get("health"),
                vendor_specific=raw_status.get("vendor_specific", {})
            )

            return MosoroMessage(
                robot_id=self.robot_id,
                vendor=self.vendor,
                type="status",
                payload=payload
            )

        except Exception as e:
            self.logger.error(f"Failed to fetch/normalize status: {e}")
            # Return error status
            return MosoroMessage(
                robot_id=self.robot_id,
                vendor=self.vendor,
                type="error",
                payload=MosoroPayload(
                    status="error",
                    health="unreachable",
                    errors=[{"code": "FETCH_FAILED", "message": str(e)}]
                )
            )

    async def handle_command(self, raw_command: Dict[str, Any]) -> bool:
        """
        Public entry point for commands coming from the gateway.
        You can add validation or preprocessing here if needed.
        """
        try:
            self.logger.info(f"Received command for {self.robot_id}: {raw_command}")
            success = await self.send_command(raw_command)
            if success:
                self.logger.info("Command executed successfully")
            else:
                self.logger.warning("Command execution failed or rejected by robot")
            return success
        except Exception as e:
            self.logger.error(f"Error handling command: {e}")
            return False

    # Optional lifecycle methods
    async def connect(self) -> bool:
        """Override if the robot requires explicit connection setup."""
        self.connected = True
        self.logger.info(f"{self.vendor} adapter {self.robot_id} connected")
        return True

    async def disconnect(self):
        """Cleanup when agent shuts down."""
        self.connected = False
        self.logger.info(f"{self.vendor} adapter {self.robot_id} disconnected")
