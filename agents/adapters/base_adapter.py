"""
Mosoro Base Adapter Template
============================

This is the official skeleton for creating new robot adapters in Mosoro v1.5.

To add support for a new robot vendor:
1. Copy this file to `adapters/my_robot.py`
2. Rename the class to `MyRobotAdapter`
3. Implement the two abstract methods:
   - `_fetch_robot_status()` → returns dict compatible with MosoroPayload
   - `send_command(command)` → executes command on the physical robot
4. Add the adapter to the main agent or registry as needed.

All adapters must produce normalized `MosoroMessage` objects.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

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


# ------------------------------------------------------------------
# Example of how a concrete adapter would look (for reference only)
# ------------------------------------------------------------------

class ExampleVendorAdapter(BaseMosoroAdapter):
    """Skeleton showing how to implement a real adapter."""

    async def _fetch_robot_status(self) -> Dict[str, Any]:
        # TODO: Replace with actual API call to the robot
        # Example using REST:
        # response = await self.session.get(f"{self.config['api_base']}/status")
        # data = response.json()

        return {
            "position": {"x": 12.34, "y": 56.78, "theta": 0.0},
            "battery": 87.5,
            "status": "moving",
            "current_task": {
                "task_id": "task-789",
                "task_type": "tote_retrieval",
                "progress": 65.0
            },
            "health": "good",
            "vendor_specific": {"speed": 1.2, "load": 45}
        }

    async def send_command(self, command: Dict[str, Any]) -> bool:
        action = command.get("action")
        self.logger.info(f"Executing {action} on ExampleVendor robot")

        # TODO: Implement actual command sending
        if action == "move_to":
            # await self.session.post(... position data ...)
            return True
        elif action == "pause":
            return True

        return False
