# Copyright 2026 Mosoro Inc.
# SPDX-License-Identifier: Apache-2.0

"""Tests for api.main — FastAPI endpoint tests."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a test client with mocked MQTT dependencies."""
    mock_subscriber = MagicMock()
    mock_subscriber.start = MagicMock()
    mock_subscriber.stop = MagicMock()
    mock_subscriber.is_connected = False
    mock_subscriber.get_fleet_size.return_value = 0
    mock_subscriber.uptime = 0.0
    mock_subscriber.get_all_robots.return_value = {}
    mock_subscriber.get_recent_events.return_value = []

    # Patch the module-level mqtt_subscriber instance and plugin helpers
    with patch("api.main.mqtt_subscriber", mock_subscriber):
        with patch("api.main.discover_plugins", return_value=[]):
            with patch("api.main.mount_plugin_routers"):
                from api.main import app

                client = TestClient(app)
                yield client


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_200(self, test_client):
        response = test_client.get("/health")
        assert response.status_code == 200

    def test_health_returns_status(self, test_client):
        response = test_client.get("/health")
        data = response.json()
        assert "status" in data


class TestRobotsEndpoint:
    """Tests for the /robots endpoint."""

    def test_robots_returns_200(self, test_client):
        response = test_client.get("/robots")
        assert response.status_code == 200

    def test_robots_returns_list(self, test_client):
        response = test_client.get("/robots")
        data = response.json()
        # Should return a list (or dict with robots key)
        assert isinstance(data, (list, dict))


class TestEventsEndpoint:
    """Tests for the /events endpoint."""

    def test_events_returns_200(self, test_client):
        response = test_client.get("/events")
        assert response.status_code == 200
