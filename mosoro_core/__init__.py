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
Mosoro Core
============

The neutral bridge for multi-vendor warehouse robot fleets.

Public API:
    Models: MosoroMessage, MosoroPayload, Position, MessageHeader, CurrentTask, ErrorDetail
    Adapters: BaseMosoroAdapter, discover_adapters
    Plugins: discover_plugins, mount_plugin_routers, MosoroPlugin
    Version: __version__
"""

from mosoro_core.adapter_registry import discover_adapters
from mosoro_core.base_adapter import BaseMosoroAdapter
from mosoro_core.models import (
    CurrentTask,
    ErrorDetail,
    MessageHeader,
    MosoroMessage,
    MosoroPayload,
    Position,
)
from mosoro_core.plugin_types import MosoroPlugin
from mosoro_core.plugins import discover_plugins, mount_plugin_routers
from mosoro_core.version import __version__

__all__ = [
    # Models
    "MosoroMessage",
    "MosoroPayload",
    "Position",
    "MessageHeader",
    "CurrentTask",
    "ErrorDetail",
    # Adapters
    "BaseMosoroAdapter",
    "discover_adapters",
    # Plugins
    "discover_plugins",
    "mount_plugin_routers",
    "MosoroPlugin",
    # Version
    "__version__",
]
