# Copyright 2026 Mosoro Inc.
# SPDX-License-Identifier: Apache-2.0

"""Shared test fixtures for Mosoro Core test suite."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

from mosoro_core.models import (
    MosoroMessage,
    MosoroPayload,
    Position,
    MessageHeader,
    CurrentTask,
    ErrorDetail,
)
from mosoro_core.plugin_types import MosoroPlugin


@pytest.fixture
def sample_position():
    """Create a sample Position for testing."""
    return Position(x=10.5, y=20.3, z=0.0, theta=1.57, map_id="warehouse-floor-1")


@pytest.fixture
def sample_payload(sample_position):
    """Create a sample MosoroPayload for testing."""
    return MosoroPayload(
        position=sample_position,
        battery=85.5,
        status="moving",
        current_task=CurrentTask(
            task_id="task-001",
            task_type="pick",
            progress=45.0,
        ),
        health="nominal",
        errors=[],
        vendor_specific={"firmware_version": "2.1.0"},
    )


@pytest.fixture
def sample_message(sample_payload):
    """Create a sample MosoroMessage for testing."""
    return MosoroMessage(
        robot_id="robot-locus-001",
        vendor="locus",
        type="status",
        payload=sample_payload,
    )


@pytest.fixture
def sample_message_dict(sample_message):
    """Create a sample MosoroMessage as a dict for testing."""
    return sample_message.model_dump(mode="json")


@pytest.fixture
def mock_mqtt_client():
    """Create a mock MQTT client for testing."""
    client = MagicMock()
    client.publish = MagicMock()
    client.subscribe = MagicMock()
    client.connect = MagicMock()
    client.disconnect = MagicMock()
    client.loop_start = MagicMock()
    client.loop_stop = MagicMock()
    return client


@pytest.fixture
def mock_plugin():
    """Create a mock MosoroPlugin for testing."""
    from fastapi import APIRouter

    router = APIRouter()

    @router.get("/health")
    async def plugin_health():
        return {"status": "ok", "plugin": "test-plugin"}

    return MosoroPlugin(
        name="test-plugin",
        version="1.0.0",
        description="A test plugin for unit testing",
        api_router=router,
        mqtt_topics=["mosoro/v1/test/#"],
    )


@pytest.fixture
def mock_plugin_with_hooks():
    """Create a mock MosoroPlugin with gateway hooks for testing."""
    hook_calls = {"on_message_received": [], "on_rule_matched": [], "on_command_sent": []}

    def on_message(topic, payload):
        hook_calls["on_message_received"].append({"topic": topic, "payload": payload})

    def on_rule(rule_name, trigger_message, action):
        hook_calls["on_rule_matched"].append({
            "rule_name": rule_name,
            "trigger_message": trigger_message,
            "action": action,
        })

    def on_command(robot_id, command):
        hook_calls["on_command_sent"].append({"robot_id": robot_id, "command": command})

    plugin = MosoroPlugin(
        name="test-hooks-plugin",
        version="1.0.0",
        description="A test plugin with hooks",
    )
    plugin.add_hook("on_message_received", on_message)
    plugin.add_hook("on_rule_matched", on_rule)
    plugin.add_hook("on_command_sent", on_command)

    return plugin, hook_calls
