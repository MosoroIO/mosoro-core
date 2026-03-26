# Copyright 2026 Mosoro Inc.
# SPDX-License-Identifier: Apache-2.0

"""Tests for mosoro_core.plugins — Plugin discovery and management."""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI

from mosoro_core.plugin_types import MosoroPlugin
from mosoro_core.plugins import (
    ENTRY_POINT_GROUP,
    discover_plugins,
    get_gateway_hooks,
    invoke_hooks,
    mount_plugin_routers,
)


class TestDiscoverPlugins:
    """Tests for the discover_plugins function."""

    @patch("mosoro_core.plugins.entry_points")
    def test_no_plugins_returns_empty_list(self, mock_ep):
        mock_ep.return_value = []
        plugins = discover_plugins()
        assert plugins == []
        mock_ep.assert_called_once_with(group=ENTRY_POINT_GROUP)

    @patch("mosoro_core.plugins.entry_points")
    def test_discovers_valid_plugin(self, mock_ep):
        mock_plugin = MosoroPlugin(name="test", version="1.0.0")
        mock_entry = MagicMock()
        mock_entry.name = "test"
        mock_entry.load.return_value = lambda: mock_plugin
        mock_ep.return_value = [mock_entry]

        plugins = discover_plugins()
        assert len(plugins) == 1
        assert plugins[0].name == "test"

    @patch("mosoro_core.plugins.entry_points")
    def test_skips_broken_plugin(self, mock_ep):
        mock_entry = MagicMock()
        mock_entry.name = "broken"
        mock_entry.load.side_effect = ImportError("Module not found")
        mock_ep.return_value = [mock_entry]

        plugins = discover_plugins()
        assert plugins == []

    @patch("mosoro_core.plugins.entry_points")
    def test_skips_non_mosoro_plugin(self, mock_ep):
        mock_entry = MagicMock()
        mock_entry.name = "wrong-type"
        mock_entry.load.return_value = lambda: "not a MosoroPlugin"
        mock_ep.return_value = [mock_entry]

        plugins = discover_plugins()
        assert plugins == []


class TestMountPluginRouters:
    """Tests for the mount_plugin_routers function."""

    def test_mounts_plugin_router(self, mock_plugin):
        app = FastAPI()
        mount_plugin_routers(app, [mock_plugin])

        # Verify the router was included by checking routes
        route_paths = [route.path for route in app.routes]
        assert "/plugins/test-plugin/health" in route_paths

    def test_skips_plugin_without_router(self):
        app = FastAPI()
        plugin = MosoroPlugin(name="no-router", version="1.0.0")
        mount_plugin_routers(app, [plugin])

        # Only default routes should exist
        initial_route_count = len(FastAPI().routes)
        assert len(app.routes) == initial_route_count

    def test_mounts_multiple_plugins(self, mock_plugin):
        from fastapi import APIRouter

        router2 = APIRouter()

        @router2.get("/status")
        async def status():
            return {"ok": True}

        plugin2 = MosoroPlugin(name="plugin-two", version="2.0.0", api_router=router2)

        app = FastAPI()
        mount_plugin_routers(app, [mock_plugin, plugin2])

        route_paths = [route.path for route in app.routes]
        assert "/plugins/test-plugin/health" in route_paths
        assert "/plugins/plugin-two/status" in route_paths


class TestGetGatewayHooks:
    """Tests for the get_gateway_hooks function."""

    def test_empty_plugins_returns_empty_hooks(self):
        hooks = get_gateway_hooks([])
        assert hooks == {}

    def test_collects_hooks_from_plugin(self, mock_plugin_with_hooks):
        plugin, _ = mock_plugin_with_hooks
        hooks = get_gateway_hooks([plugin])

        assert "on_message_received" in hooks
        assert "on_rule_matched" in hooks
        assert "on_command_sent" in hooks
        assert len(hooks["on_message_received"]) == 1

    def test_collects_hooks_from_multiple_plugins(self, mock_plugin_with_hooks):
        plugin1, _ = mock_plugin_with_hooks

        plugin2 = MosoroPlugin(name="plugin2", version="1.0.0")
        plugin2.add_hook("on_message_received", lambda topic, payload: None)

        hooks = get_gateway_hooks([plugin1, plugin2])
        assert len(hooks["on_message_received"]) == 2


class TestInvokeHooks:
    """Tests for the invoke_hooks function."""

    def test_invokes_registered_hooks(self, mock_plugin_with_hooks):
        plugin, hook_calls = mock_plugin_with_hooks
        hooks = get_gateway_hooks([plugin])

        invoke_hooks(hooks, "on_message_received", topic="test/topic", payload={"key": "value"})

        assert len(hook_calls["on_message_received"]) == 1
        assert hook_calls["on_message_received"][0]["topic"] == "test/topic"

    def test_handles_hook_error_gracefully(self):
        def bad_hook(**kwargs):
            raise RuntimeError("Plugin crashed!")

        hooks = {"on_message_received": [bad_hook]}

        # Should not raise
        invoke_hooks(hooks, "on_message_received", topic="test", payload={})

    def test_invokes_nothing_for_unknown_event(self):
        hooks = {"on_message_received": [lambda **kw: None]}
        # Should not raise
        invoke_hooks(hooks, "on_nonexistent_event")

    def test_invokes_multiple_hooks_in_order(self):
        call_order = []

        def hook1(**kwargs):
            call_order.append("hook1")

        def hook2(**kwargs):
            call_order.append("hook2")

        hooks = {"on_command_sent": [hook1, hook2]}
        invoke_hooks(hooks, "on_command_sent", robot_id="r1", command={})

        assert call_order == ["hook1", "hook2"]
