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
Mosoro Plugin Discovery
========================

Discovers and loads plugins registered via Python entry points.
Premium modules register under the "mosoro.plugins" entry point group
in their pyproject.toml.

Example entry point registration in a premium module's pyproject.toml:

    [project.entry-points."mosoro.plugins"]
    security_pro = "mosoro_security_pro:plugin"
"""

import logging
from importlib.metadata import entry_points
from typing import Any, Callable, Dict, List, Optional

from mosoro_core.plugin_types import MosoroPlugin

logger = logging.getLogger("mosoro.plugins")

ENTRY_POINT_GROUP = "mosoro.plugins"


def discover_plugins() -> List[MosoroPlugin]:
    """Scan for and load all registered Mosoro plugins.
    
    Discovers plugins via Python entry points registered under
    the "mosoro.plugins" group. Each entry point should be a callable
    that returns a MosoroPlugin instance.
    
    Returns:
        List of discovered MosoroPlugin instances.
        Broken plugins are logged and skipped.
    """
    plugins: List[MosoroPlugin] = []
    
    discovered = entry_points(group=ENTRY_POINT_GROUP)
    
    if not discovered:
        logger.info("No plugins discovered under '%s' entry point group.", ENTRY_POINT_GROUP)
        return plugins
    
    for ep in discovered:
        try:
            logger.info("Loading plugin entry point: %s", ep.name)
            plugin_factory = ep.load()
            plugin = plugin_factory()
            
            if not isinstance(plugin, MosoroPlugin):
                logger.warning(
                    "Plugin '%s' returned %s instead of MosoroPlugin. Skipping.",
                    ep.name, type(plugin).__name__
                )
                continue
            
            logger.info(
                "Loaded plugin: %s v%s — %s",
                plugin.name, plugin.version, plugin.description or "(no description)"
            )
            plugins.append(plugin)
            
        except Exception:
            logger.exception("Failed to load plugin '%s'. Skipping.", ep.name)
    
    logger.info("Plugin discovery complete. %d plugin(s) loaded.", len(plugins))
    return plugins


def mount_plugin_routers(app: Any, plugins: List[MosoroPlugin]) -> None:
    """Mount plugin FastAPI routers onto the main application.
    
    Each plugin's router is mounted under /plugins/{plugin_name}/.
    
    Args:
        app: The FastAPI application instance.
        plugins: List of discovered plugins.
    """
    for plugin in plugins:
        if plugin.api_router is not None:
            prefix = f"/plugins/{plugin.name}"
            try:
                app.include_router(
                    plugin.api_router,
                    prefix=prefix,
                    tags=[f"plugin:{plugin.name}"],
                )
                logger.info("Mounted plugin router: %s -> %s/*", plugin.name, prefix)
            except Exception:
                logger.exception(
                    "Failed to mount router for plugin '%s'. Skipping.", plugin.name
                )


def get_gateway_hooks(plugins: List[MosoroPlugin]) -> Dict[str, List[Callable]]:
    """Collect all gateway hooks from discovered plugins.
    
    Returns a dict mapping event names to lists of handler functions.
    
    Supported events:
        - 'on_message_received': Called for every incoming MQTT message
        - 'on_rule_matched': Called when a gateway rule fires
        - 'on_command_sent': Called when a command is published to a robot
    
    Args:
        plugins: List of discovered plugins.
        
    Returns:
        Dict mapping event name -> list of handler callables.
    """
    hooks: Dict[str, List[Callable]] = {}
    
    for plugin in plugins:
        for event, handlers in plugin.gateway_hooks.items():
            if event not in hooks:
                hooks[event] = []
            hooks[event].extend(handlers)
            logger.info(
                "Registered %d hook(s) for '%s' from plugin '%s'.",
                len(handlers), event, plugin.name
            )
    
    return hooks


def invoke_hooks(
    hooks: Dict[str, List[Callable]],
    event: str,
    **kwargs: Any,
) -> None:
    """Safely invoke all registered hooks for a given event.
    
    Each hook is called in a try/except block to prevent plugin errors
    from crashing the gateway or API.
    
    Args:
        hooks: Dict of event -> handler lists (from get_gateway_hooks).
        event: The event name to invoke.
        **kwargs: Arguments passed to each hook handler.
    """
    handlers = hooks.get(event, [])
    for handler in handlers:
        try:
            handler(**kwargs)
        except Exception:
            logger.exception(
                "Error in plugin hook for event '%s' (handler: %s). Continuing.",
                event, getattr(handler, "__qualname__", repr(handler))
            )
