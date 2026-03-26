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
Mosoro API Pydantic Models
===========================

API-specific request/response models. Imports shared models from mosoro_core.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# Re-export shared models for convenience
from mosoro_core.models import (
    CurrentTask,
    ErrorDetail,
    MessageHeader,
    MosoroMessage,
    MosoroPayload,
    Position,
)


# ---------------------------------------------------------------------------
# API Response Models
# ---------------------------------------------------------------------------

class RobotStatusResponse(BaseModel):
    """API response for a single robot's status."""
    robot_id: str
    vendor: str
    status: Optional[str] = None
    position: Optional[Position] = None
    battery: Optional[float] = None
    health: Optional[str] = None
    current_task: Optional[CurrentTask] = None
    last_updated: float
    is_online: bool = True


class FleetStatusResponse(BaseModel):
    """API response for the entire fleet."""
    total_robots: int
    robots: List[RobotStatusResponse]
    by_vendor: Dict[str, int] = Field(default_factory=dict)
    by_status: Dict[str, int] = Field(default_factory=dict)


class EventResponse(BaseModel):
    """API response for a fleet event."""
    robot_id: str
    vendor: str
    topic: str
    payload: Dict[str, Any]
    received_at: float


# ---------------------------------------------------------------------------
# API Request Models
# ---------------------------------------------------------------------------

class TaskAssignRequest(BaseModel):
    """Request to assign a task to a robot."""
    robot_id: str
    action: str = Field(..., description="Command action (e.g., 'move_to', 'pick', 'pause')")
    position: Optional[Position] = None
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TaskAssignResponse(BaseModel):
    """Response after assigning a task."""
    success: bool
    message: str
    task_id: Optional[str] = None
    robot_id: str


# ---------------------------------------------------------------------------
# Auth Models
# ---------------------------------------------------------------------------

class TokenRequest(BaseModel):
    """Request for an API token."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Response with an API token."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """API health check response."""
    status: str = "ok"
    version: str = "1.0"
    mqtt_connected: bool = False
    fleet_size: int = 0
    uptime_seconds: float = 0.0
