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
Mosoro Unified API
===================

FastAPI application providing REST endpoints and WebSocket for the
Mosoro robot fleet management platform.

Endpoints:
    GET  /health          - Health check
    GET  /robots          - List all robots with status
    GET  /robots/{id}     - Get a specific robot's status
    POST /tasks           - Assign a task to a robot
    GET  /events          - Get recent fleet events
    WS   /ws/fleet        - Real-time fleet updates via WebSocket
    POST /auth/token      - Get a JWT access token

Run with:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from api.models import (
    EventResponse,
    FleetStatusResponse,
    HealthResponse,
    RobotStatusResponse,
    TaskAssignRequest,
    TaskAssignResponse,
    TokenRequest,
    TokenResponse,
)
from api.mqtt_subscriber import MQTTFleetSubscriber
from mosoro_core.models import Position
from mosoro_core.plugins import discover_plugins, mount_plugin_routers

logger = logging.getLogger("mosoro.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# Global MQTT subscriber instance
mqtt_subscriber = MQTTFleetSubscriber()

# WebSocket connection manager
ws_connections: List[WebSocket] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: start/stop MQTT subscriber and plugins."""
    logger.info("Starting Mosoro API...")
    mqtt_subscriber.start()

    # Discover and mount plugins
    plugins = discover_plugins()
    mount_plugin_routers(app, plugins)
    app.state.plugins = plugins
    logger.info("Mosoro API started with %d plugin(s).", len(plugins))

    yield
    logger.info("Stopping Mosoro API...")
    mqtt_subscriber.stop()


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mosoro Fleet API",
    description="Unified REST API for multi-vendor warehouse robot fleet management",
    version="1.0.0",
    license_info={"name": "Apache 2.0", "url": "https://www.apache.org/licenses/LICENSE-2.0"},
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Auth dependency (optional — import from security.auth when available)
# ---------------------------------------------------------------------------


def get_optional_auth():
    """Optional auth dependency. Returns None if auth module not available."""
    try:
        from security.auth import get_current_user

        return get_current_user
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version="1.0",
        mqtt_connected=mqtt_subscriber.is_connected,
        fleet_size=mqtt_subscriber.get_fleet_size(),
        uptime_seconds=mqtt_subscriber.uptime,
    )


# ---------------------------------------------------------------------------
# Robot Endpoints
# ---------------------------------------------------------------------------


@app.get("/robots", response_model=FleetStatusResponse, tags=["Robots"])
async def list_robots():
    """List all robots with their current status."""
    robots_data = mqtt_subscriber.get_all_robots()

    robots = []
    by_vendor: Dict[str, int] = {}
    by_status: Dict[str, int] = {}

    for robot_id, state in robots_data.items():
        data = state.get("data", {})
        payload = data.get("payload", {})
        vendor = state.get("vendor", "unknown")
        robot_status = payload.get("status", "unknown")

        # Count by vendor and status
        by_vendor[vendor] = by_vendor.get(vendor, 0) + 1
        by_status[robot_status] = by_status.get(robot_status, 0) + 1

        position_data = payload.get("position")
        position = Position(**position_data) if position_data else None

        robots.append(
            RobotStatusResponse(
                robot_id=robot_id,
                vendor=vendor,
                status=robot_status,
                position=position,
                battery=payload.get("battery"),
                health=payload.get("health"),
                current_task=payload.get("current_task"),
                last_updated=state.get("last_updated", 0),
                is_online=True,
            )
        )

    return FleetStatusResponse(
        total_robots=len(robots),
        robots=robots,
        by_vendor=by_vendor,
        by_status=by_status,
    )


@app.get("/robots/{robot_id}", response_model=RobotStatusResponse, tags=["Robots"])
async def get_robot(robot_id: str):
    """Get a specific robot's current status."""
    state = mqtt_subscriber.get_robot(robot_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Robot '{robot_id}' not found",
        )

    data = state.get("data", {})
    payload = data.get("payload", {})
    position_data = payload.get("position")
    position = Position(**position_data) if position_data else None

    return RobotStatusResponse(
        robot_id=robot_id,
        vendor=state.get("vendor", "unknown"),
        status=payload.get("status"),
        position=position,
        battery=payload.get("battery"),
        health=payload.get("health"),
        current_task=payload.get("current_task"),
        last_updated=state.get("last_updated", 0),
        is_online=True,
    )


# ---------------------------------------------------------------------------
# Task Endpoints
# ---------------------------------------------------------------------------


@app.post("/tasks", response_model=TaskAssignResponse, tags=["Tasks"])
async def assign_task(request: TaskAssignRequest):
    """Assign a task (command) to a robot."""
    # Verify robot exists
    state = mqtt_subscriber.get_robot(request.robot_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Robot '{request.robot_id}' not found",
        )

    # Build command payload
    task_id = str(uuid4())
    command = {
        "header": {"message_id": str(uuid4()), "version": "1.0"},
        "robot_id": request.robot_id,
        "vendor": state.get("vendor", "unknown"),
        "type": "command",
        "payload": {
            "action": request.action,
            "task_id": task_id,
            **({"position": request.position.model_dump()} if request.position else {}),
            **(request.parameters or {}),
        },
    }

    # Publish via MQTT
    success = mqtt_subscriber.publish_command(request.robot_id, command)

    if success:
        return TaskAssignResponse(
            success=True,
            message=f"Task '{request.action}' assigned to robot '{request.robot_id}'",
            task_id=task_id,
            robot_id=request.robot_id,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to publish command. MQTT may be disconnected.",
        )


# ---------------------------------------------------------------------------
# Events Endpoint
# ---------------------------------------------------------------------------


@app.get("/events", response_model=List[EventResponse], tags=["Events"])
async def get_events(limit: int = 50):
    """Get recent fleet events."""
    events = mqtt_subscriber.get_recent_events(limit)
    return [
        EventResponse(
            robot_id=e.get("robot_id", "unknown"),
            vendor=e.get("vendor", "unknown"),
            topic=e.get("topic", ""),
            payload=e.get("payload", {}),
            received_at=e.get("received_at", 0),
        )
        for e in events
    ]


# ---------------------------------------------------------------------------
# WebSocket for Real-Time Fleet Updates
# ---------------------------------------------------------------------------


@app.websocket("/ws/fleet")
async def websocket_fleet(websocket: WebSocket):
    """WebSocket endpoint for real-time fleet updates."""
    await websocket.accept()
    ws_connections.append(websocket)
    logger.info(f"WebSocket client connected (total: {len(ws_connections)})")

    # Register callback for MQTT messages
    message_queue: asyncio.Queue = asyncio.Queue()

    def on_mqtt_message(msg: Dict[str, Any]):
        try:
            message_queue.put_nowait(msg)
        except asyncio.QueueFull:
            pass

    mqtt_subscriber.register_ws_callback(on_mqtt_message)

    try:
        # Send initial fleet state
        robots = mqtt_subscriber.get_all_robots()
        await websocket.send_json(
            {
                "type": "initial_state",
                "robots": {rid: state for rid, state in robots.items()},
            }
        )

        # Stream updates
        while True:
            try:
                msg = await asyncio.wait_for(message_queue.get(), timeout=30.0)
                await websocket.send_json(msg)
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat", "timestamp": time.time()})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        mqtt_subscriber.unregister_ws_callback(on_mqtt_message)
        if websocket in ws_connections:
            ws_connections.remove(websocket)


# ---------------------------------------------------------------------------
# Auth Endpoints (stub — uses security.auth when available)
# ---------------------------------------------------------------------------


@app.post("/auth/token", response_model=TokenResponse, tags=["Auth"])
async def get_token(request: TokenRequest):
    """Get a JWT access token (stub for Phase 1)."""
    try:
        from security.auth import JWT_EXPIRATION_MINUTES, create_access_token

        # Simple validation (replace with proper user store in production)
        if request.username == "admin" and request.password == "mosoro-admin":
            token = create_access_token(data={"sub": request.username, "role": "admin"})
            return TokenResponse(
                access_token=token,
                token_type="bearer",
                expires_in=JWT_EXPIRATION_MINUTES * 60,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Auth module not available. Install PyJWT.",
        )
