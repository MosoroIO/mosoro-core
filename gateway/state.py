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
Mosoro Gateway In-Memory State Store
=====================================

Thread-safe in-memory state store with TTL for tracking robot positions,
health, and status. Used by the gateway to make routing decisions.

Future: Replace with persistent storage layer (e.g., Redis or database).
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("mosoro.gateway.state")

# Default TTL for robot state entries (seconds)
DEFAULT_TTL = 60.0


class RobotState:
    """Represents the current state of a single robot."""

    def __init__(self, robot_id: str, vendor: str, data: Dict[str, Any]):
        self.robot_id = robot_id
        self.vendor = vendor
        self.data = data
        self.last_updated = time.time()

    @property
    def is_expired(self) -> bool:
        """Check if this state entry has expired."""
        return (time.time() - self.last_updated) > DEFAULT_TTL

    @property
    def position(self) -> Optional[Dict[str, float]]:
        """Get the robot's current position."""
        payload = self.data.get("payload", {})
        return payload.get("position")

    @property
    def status(self) -> Optional[str]:
        """Get the robot's current status."""
        payload = self.data.get("payload", {})
        return payload.get("status")

    @property
    def battery(self) -> Optional[float]:
        """Get the robot's battery level."""
        payload = self.data.get("payload", {})
        return payload.get("battery")

    @property
    def health(self) -> Optional[str]:
        """Get the robot's health status."""
        payload = self.data.get("payload", {})
        return payload.get("health")

    @property
    def current_task(self) -> Optional[Dict[str, Any]]:
        """Get the robot's current task."""
        payload = self.data.get("payload", {})
        return payload.get("current_task")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "robot_id": self.robot_id,
            "vendor": self.vendor,
            "data": self.data,
            "last_updated": self.last_updated,
            "is_expired": self.is_expired,
        }


class FleetStateStore:
    """
    In-memory state store for the entire robot fleet.

    Thread-safe via asyncio.Lock. Supports TTL-based expiration.
    """

    def __init__(self, ttl: float = DEFAULT_TTL):
        self._robots: Dict[str, RobotState] = {}
        self._events: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._ttl = ttl
        self._max_events = 1000  # Keep last N events in memory

    async def update_robot(self, robot_id: str, vendor: str, data: Dict[str, Any]):
        """Update or create a robot state entry."""
        async with self._lock:
            self._robots[robot_id] = RobotState(robot_id, vendor, data)
            logger.debug(f"Updated state for robot {robot_id}")

    async def get_robot(self, robot_id: str) -> Optional[RobotState]:
        """Get a robot's current state (returns None if expired or not found)."""
        async with self._lock:
            state = self._robots.get(robot_id)
            if state and not state.is_expired:
                return state
            return None

    async def get_all_robots(self, include_expired: bool = False) -> Dict[str, RobotState]:
        """Get all robot states."""
        async with self._lock:
            if include_expired:
                return dict(self._robots)
            return {
                rid: state
                for rid, state in self._robots.items()
                if not state.is_expired
            }

    async def get_robots_by_vendor(self, vendor: str) -> List[RobotState]:
        """Get all robots of a specific vendor."""
        async with self._lock:
            return [
                state
                for state in self._robots.values()
                if state.vendor == vendor and not state.is_expired
            ]

    async def get_robots_by_status(self, status: str) -> List[RobotState]:
        """Get all robots with a specific status (e.g., 'idle')."""
        async with self._lock:
            return [
                state
                for state in self._robots.values()
                if state.status == status and not state.is_expired
            ]

    async def get_nearest_robot(
        self,
        x: float,
        y: float,
        vendor: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[RobotState]:
        """
        Find the nearest robot to a given position.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            vendor: Filter by vendor (optional).
            status: Filter by status (optional, e.g., 'idle').

        Returns:
            The nearest matching RobotState, or None.
        """
        async with self._lock:
            best = None
            best_dist = float("inf")

            for state in self._robots.values():
                if state.is_expired:
                    continue
                if vendor and state.vendor != vendor:
                    continue
                if status and state.status != status:
                    continue

                pos = state.position
                if not pos:
                    continue

                dx = pos.get("x", 0) - x
                dy = pos.get("y", 0) - y
                dist = (dx * dx + dy * dy) ** 0.5

                if dist < best_dist:
                    best_dist = dist
                    best = state

            return best

    async def add_event(self, event: Dict[str, Any]):
        """Store an event in the event log."""
        async with self._lock:
            self._events.append({
                **event,
                "_received_at": time.time(),
            })
            # Trim to max size
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]

    async def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the most recent events."""
        async with self._lock:
            return list(self._events[-limit:])

    async def remove_robot(self, robot_id: str):
        """Remove a robot from the state store."""
        async with self._lock:
            self._robots.pop(robot_id, None)
            logger.info(f"Removed robot {robot_id} from state store")

    async def cleanup_expired(self):
        """Remove all expired robot entries."""
        async with self._lock:
            expired = [
                rid for rid, state in self._robots.items() if state.is_expired
            ]
            for rid in expired:
                del self._robots[rid]
                logger.info(f"Cleaned up expired state for robot {rid}")
            return len(expired)

    async def get_fleet_summary(self) -> Dict[str, Any]:
        """Get a summary of the fleet state."""
        async with self._lock:
            active = [s for s in self._robots.values() if not s.is_expired]
            return {
                "total_robots": len(active),
                "by_vendor": _count_by(active, lambda s: s.vendor),
                "by_status": _count_by(active, lambda s: s.status or "unknown"),
                "recent_events": len(self._events),
            }


def _count_by(items: list, key_fn) -> Dict[str, int]:
    """Count items by a key function."""
    counts: Dict[str, int] = {}
    for item in items:
        k = key_fn(item)
        counts[k] = counts.get(k, 0) + 1
    return counts
