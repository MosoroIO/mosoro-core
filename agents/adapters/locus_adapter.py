"""
Mosoro Adapter for Locus Robotics AMRs
======================================

Locus uses a REST API for status and commands.
This adapter normalizes Locus data into the common MosoroMessage schema.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp

from agents.adapters.base_adapter import BaseMosoroAdapter
from mosoro_core.models import MosoroMessage


class LocusAdapter(BaseMosoroAdapter):
    """Adapter for Locus Robotics autonomous mobile robots."""

    vendor_name = "locus"
    
    def __init__(self, robot_id: str, config: Dict[str, Any]):
        super().__init__(robot_id, config)
        self.api_base = config.get("api_base_url", "http://localhost:8080")
        self.api_key = config.get("api_key")
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> bool:
        """Initialize HTTP session for Locus API."""
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        )
        self.connected = True
        self.logger.info(f"Locus adapter {self.robot_id} connected to {self.api_base}")
        return True

    async def disconnect(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
        self.connected = False
        self.logger.info(f"Locus adapter {self.robot_id} disconnected")

    async def _fetch_robot_status(self) -> Dict[str, Any]:
        """Fetch status from Locus REST API and normalize it."""
        if not self.session:
            await self.connect()

        try:
            async with self.session.get(f"{self.api_base}/robots/{self.robot_id}/status") as resp:
                if resp.status != 200:
                    self.logger.error(f"Locus API returned {resp.status}")
                    raise Exception(f"HTTP {resp.status}")

                data = await resp.json()

                # Normalize Locus-specific fields to Mosoro schema
                return {
                    "position": {
                        "x": data.get("x", 0.0),
                        "y": data.get("y", 0.0),
                        "theta": data.get("theta", 0.0),
                        "map_id": data.get("map_id")
                    },
                    "battery": data.get("battery_level", 0.0),
                    "status": self._map_locus_status(data.get("state", "unknown")),
                    "current_task": {
                        "task_id": data.get("current_task_id"),
                        "task_type": data.get("task_type", "unknown"),
                        "progress": data.get("task_progress", 0.0)
                    } if data.get("current_task_id") else None,
                    "health": "good" if data.get("faults") is None else "warning",
                    "vendor_specific": {
                        "locus_state": data.get("state"),
                        "speed": data.get("speed"),
                        "load_status": data.get("load_status")
                    }
                }
        except Exception as e:
            self.logger.error(f"Failed to fetch Locus status: {e}")
            raise

    def _map_locus_status(self, locus_state: str) -> str:
        """Map Locus states to Mosoro standard status."""
        mapping = {
            "IDLE": "idle",
            "MOVING": "moving",
            "CHARGING": "charging",
            "ERROR": "error",
            "PAUSED": "idle"
        }
        return mapping.get(locus_state.upper(), "unknown")

    async def send_command(self, command: Dict[str, Any]) -> bool:
        """Send command to Locus robot via REST API."""
        if not self.session:
            await self.connect()

        action = command.get("action")
        try:
            if action == "move_to":
                payload = {
                    "x": command["position"]["x"],
                    "y": command["position"]["y"],
                    "theta": command["position"].get("theta", 0.0)
                }
                async with self.session.post(f"{self.api_base}/robots/{self.robot_id}/navigate", json=payload) as resp:
                    return resp.status == 200

            elif action == "pause":
                async with self.session.post(f"{self.api_base}/robots/{self.robot_id}/pause") as resp:
                    return resp.status == 200

            elif action == "resume":
                async with self.session.post(f"{self.api_base}/robots/{self.robot_id}/resume") as resp:
                    return resp.status == 200

            self.logger.warning(f"Unknown command action: {action}")
            return False

        except Exception as e:
            self.logger.error(f"Failed to send command to Locus: {e}")
            return False
