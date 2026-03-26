"""
Mosoro Adapter for Geekplus (Seer) AMRs
=======================================

Geekplus / Seer robots are widely used in goods-to-person and tote-moving applications.
This adapter connects via their REST API (common in warehouse deployments).
"""

import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp

from agents.adapters.base_adapter import BaseMosoroAdapter
from mosoro_core.models import MosoroPayload, Position


class GeekplusAdapter(BaseMosoroAdapter):
    """
    Adapter for Geekplus / Seer autonomous mobile robots.
    
    Follows the same pattern as LocusAdapter and StretchAdapter.
    """

    vendor_name = "geekplus"   # Used by auto-discovery

    def __init__(self, robot_id: str, config: Dict[str, Any]):
        super().__init__(robot_id, config)
        self.api_base = config.get("api_base_url", "http://localhost:8080")
        self.api_key = config.get("api_key")
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> bool:
        """Initialize HTTP session for Geekplus API."""
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        self.session = aiohttp.ClientSession(headers=headers)
        self.connected = True
        self.logger.info(f"Geekplus adapter {self.robot_id} connected to {self.api_base}")
        return True

    async def disconnect(self):
        """Close HTTP session on shutdown."""
        if self.session:
            await self.session.close()
        self.connected = False
        self.logger.info(f"Geekplus adapter {self.robot_id} disconnected")

    async def _fetch_robot_status(self) -> Dict[str, Any]:
        """Fetch status from Geekplus REST API and normalize it."""
        if not self.session:
            await self.connect()

        try:
            async with self.session.get(f"{self.api_base}/robots/{self.robot_id}/status") as resp:
                if resp.status != 200:
                    self.logger.error(f"Geekplus API returned status {resp.status}")
                    raise Exception(f"HTTP error {resp.status}")

                data = await resp.json()

                # Normalize Geekplus fields to Mosoro standard schema
                return {
                    "position": {
                        "x": data.get("x", 0.0),
                        "y": data.get("y", 0.0),
                        "theta": data.get("theta", 0.0),
                        "map_id": data.get("current_map")
                    },
                    "battery": data.get("battery_percent", 0.0),
                    "status": self._map_geekplus_status(data.get("status", "unknown")),
                    "current_task": {
                        "task_id": data.get("current_task_id"),
                        "task_type": data.get("task_type", "unknown"),
                        "progress": data.get("task_progress", 0.0)
                    } if data.get("current_task_id") else None,
                    "health": "good" if not data.get("fault_code") else "warning",
                    "vendor_specific": {
                        "geekplus_status": data.get("status"),
                        "load_weight": data.get("load_weight_kg"),
                        "speed": data.get("current_speed")
                    }
                }
        except Exception as e:
            self.logger.error(f"Failed to fetch Geekplus status for {self.robot_id}: {e}")
            raise

    def _map_geekplus_status(self, raw_status: str) -> str:
        """Map Geekplus status strings to Mosoro standard status values."""
        mapping = {
            "IDLE": "idle",
            "MOVING": "moving",
            "WORKING": "working",
            "CHARGING": "charging",
            "ERROR": "error",
            "PAUSED": "idle",
            "OFFLINE": "offline"
        }
        return mapping.get(raw_status.upper(), "unknown")

    async def send_command(self, command: Dict[str, Any]) -> bool:
        """Send command to Geekplus robot via REST API."""
        if not self.session:
            await self.connect()

        action = command.get("action")
        self.logger.info(f"Sending {action} command to Geekplus robot {self.robot_id}")

        try:
            if action == "move_to":
                payload = {
                    "x": command["position"]["x"],
                    "y": command["position"]["y"],
                    "theta": command["position"].get("theta", 0.0)
                }
                async with self.session.post(
                    f"{self.api_base}/robots/{self.robot_id}/navigate", json=payload
                ) as resp:
                    return resp.status in (200, 202)

            elif action == "pause":
                async with self.session.post(f"{self.api_base}/robots/{self.robot_id}/pause") as resp:
                    return resp.status in (200, 202)

            elif action == "resume":
                async with self.session.post(f"{self.api_base}/robots/{self.robot_id}/resume") as resp:
                    return resp.status in (200, 202)

            self.logger.warning(f"Unsupported command action: {action}")
            return False

        except Exception as e:
            self.logger.error(f"Failed to send command to Geekplus: {e}")
            return False
