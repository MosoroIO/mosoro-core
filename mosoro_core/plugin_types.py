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
Mosoro Plugin Types
====================

Defines the interface that premium modules implement to extend mosoro-core.
Plugins register via Python entry points under the "mosoro.plugins" group.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol

# Use string type hint for FastAPI APIRouter to avoid hard dependency
# Premium modules that provide routers will import FastAPI themselves


class OnMessageReceived(Protocol):
    """Hook called for every incoming MQTT message (read-only)."""
    def __call__(self, topic: str, payload: Dict[str, Any]) -> None: ...


class OnRuleMatched(Protocol):
    """Hook called when a gateway rule fires."""
    def __call__(self, rule_name: str, trigger_message: Dict[str, Any], action: Dict[str, Any]) -> None: ...


class OnCommandSent(Protocol):
    """Hook called when a command is published to a robot."""
    def __call__(self, robot_id: str, command: Dict[str, Any]) -> None: ...


@dataclass
class MosoroPlugin:
    """
    Plugin descriptor returned by each premium module's entry point.
    
    All fields are optional — plugins implement only what they need.
    
    Example usage in a premium module's __init__.py:
        
        from mosoro_core.plugin_types import MosoroPlugin
        from my_plugin.router import router
        
        def plugin() -> MosoroPlugin:
            return MosoroPlugin(
                name="security-pro",
                version="1.0.0",
                api_router=router,
                mqtt_topics=["mosoro/v1/security/#"],
            )
    """
    name: str
    version: str = "0.0.0"
    description: str = ""
    
    # FastAPI APIRouter instance (typed as Any to avoid hard FastAPI dependency)
    api_router: Optional[Any] = None
    
    # Additional MQTT topics this plugin wants to subscribe to
    mqtt_topics: List[str] = field(default_factory=list)
    
    # Gateway hook functions
    gateway_hooks: Dict[str, List[Callable]] = field(default_factory=dict)
    
    def add_hook(self, event: str, handler: Callable) -> None:
        """Register a hook handler for a gateway event.
        
        Supported events: 'on_message_received', 'on_rule_matched', 'on_command_sent'
        """
        if event not in self.gateway_hooks:
            self.gateway_hooks[event] = []
        self.gateway_hooks[event].append(handler)
