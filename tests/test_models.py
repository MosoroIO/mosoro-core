# Copyright 2026 Mosoro Inc.
# SPDX-License-Identifier: Apache-2.0

"""Tests for mosoro_core.models — MosoroMessage schema validation."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from mosoro_core.models import (
    MosoroMessage,
    MosoroPayload,
    Position,
    MessageHeader,
    CurrentTask,
    ErrorDetail,
)


class TestPosition:
    """Tests for the Position model."""

    def test_create_position_minimal(self):
        pos = Position(x=1.0, y=2.0)
        assert pos.x == 1.0
        assert pos.y == 2.0
        assert pos.z is None
        assert pos.theta is None
        assert pos.map_id is None

    def test_create_position_full(self):
        pos = Position(x=1.0, y=2.0, z=3.0, theta=1.57, map_id="floor-1")
        assert pos.z == 3.0
        assert pos.theta == 1.57
        assert pos.map_id == "floor-1"


class TestMosoroPayload:
    """Tests for the MosoroPayload model."""

    def test_create_empty_payload(self):
        payload = MosoroPayload()
        assert payload.position is None
        assert payload.battery is None
        assert payload.status is None
        assert payload.current_task is None

    def test_battery_range_valid(self):
        payload = MosoroPayload(battery=50.0)
        assert payload.battery == 50.0

    def test_battery_range_zero(self):
        payload = MosoroPayload(battery=0.0)
        assert payload.battery == 0.0

    def test_battery_range_full(self):
        payload = MosoroPayload(battery=100.0)
        assert payload.battery == 100.0

    def test_battery_below_zero_invalid(self):
        with pytest.raises(ValidationError):
            MosoroPayload(battery=-1.0)

    def test_battery_above_100_invalid(self):
        with pytest.raises(ValidationError):
            MosoroPayload(battery=101.0)

    def test_valid_statuses(self):
        for status in ["idle", "moving", "working", "charging", "error", "offline"]:
            payload = MosoroPayload(status=status)
            assert payload.status == status

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            MosoroPayload(status="flying")

    def test_vendor_specific_defaults_to_empty_dict(self):
        payload = MosoroPayload()
        assert payload.vendor_specific == {}


class TestMosoroMessage:
    """Tests for the MosoroMessage model."""

    def test_create_minimal_message(self):
        msg = MosoroMessage(robot_id="robot-001", vendor="locus", type="status")
        assert msg.robot_id == "robot-001"
        assert msg.vendor == "locus"
        assert msg.type == "status"
        assert msg.header.version == "1.0"
        assert msg.header.message_id is not None

    def test_valid_vendors(self):
        for vendor in ["locus", "stretch", "seer", "geekplus", "mir", "ur", "fetch", "other"]:
            msg = MosoroMessage(robot_id="r1", vendor=vendor, type="status")
            assert msg.vendor == vendor

    def test_invalid_vendor(self):
        with pytest.raises(ValidationError):
            MosoroMessage(robot_id="r1", vendor="unknown_vendor", type="status")

    def test_valid_types(self):
        for msg_type in ["status", "event", "command", "traffic_update", "birth", "error"]:
            msg = MosoroMessage(robot_id="r1", vendor="locus", type=msg_type)
            assert msg.type == msg_type

    def test_invalid_type(self):
        with pytest.raises(ValidationError):
            MosoroMessage(robot_id="r1", vendor="locus", type="invalid_type")

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            MosoroMessage(
                robot_id="r1", vendor="locus", type="status",
                extra_field="not_allowed"
            )

    def test_json_roundtrip(self, sample_message):
        json_str = sample_message.model_dump_json()
        restored = MosoroMessage.model_validate_json(json_str)
        assert restored.robot_id == sample_message.robot_id
        assert restored.vendor == sample_message.vendor
        assert restored.type == sample_message.type
        assert restored.payload.battery == sample_message.payload.battery

    def test_dict_roundtrip(self, sample_message):
        msg_dict = sample_message.model_dump()
        restored = MosoroMessage.model_validate(msg_dict)
        assert restored.robot_id == sample_message.robot_id

    def test_timestamp_auto_generated(self):
        msg = MosoroMessage(robot_id="r1", vendor="locus", type="status")
        assert isinstance(msg.timestamp, datetime)

    def test_message_id_auto_generated(self):
        msg1 = MosoroMessage(robot_id="r1", vendor="locus", type="status")
        msg2 = MosoroMessage(robot_id="r1", vendor="locus", type="status")
        assert msg1.header.message_id != msg2.header.message_id


class TestErrorDetail:
    """Tests for the ErrorDetail model."""

    def test_create_error(self):
        error = ErrorDetail(code="E001", message="Motor overheated")
        assert error.code == "E001"
        assert error.message == "Motor overheated"


class TestCurrentTask:
    """Tests for the CurrentTask model."""

    def test_create_task(self):
        task = CurrentTask(task_id="t1", task_type="pick", progress=50.0)
        assert task.progress == 50.0

    def test_progress_defaults_to_zero(self):
        task = CurrentTask(task_id="t1", task_type="pick")
        assert task.progress == 0.0

    def test_progress_range_invalid(self):
        with pytest.raises(ValidationError):
            CurrentTask(task_id="t1", task_type="pick", progress=150.0)
