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
Mosoro Adapter Registry
========================

Discovers robot adapters registered via Python entry points under the
``mosoro.adapters`` group. This allows adapter packages (like
mosoro-adapters-community) to be installed via pip and automatically
discovered at runtime.

Example entry point registration in an adapter package's pyproject.toml::

    [project.entry-points."mosoro.adapters"]
    fetch = "adapters.fetch:FetchAdapter"
    locus = "adapters.locus:LocusAdapter"
"""

import logging
from importlib.metadata import entry_points
from typing import Dict, Type

from mosoro_core.base_adapter import BaseMosoroAdapter

logger = logging.getLogger("mosoro.adapter_registry")

ADAPTER_ENTRY_POINT_GROUP = "mosoro.adapters"


def discover_adapters() -> Dict[str, Type[BaseMosoroAdapter]]:
    """Discover all adapters registered via entry points.

    Scans the ``mosoro.adapters`` entry point group for installed adapter
    packages. Each entry point name is the vendor key (e.g., "fetch",
    "locus") and the value is the adapter class.

    Returns:
        Dict mapping vendor name to adapter class.
        Broken or invalid entry points are logged and skipped.
    """
    adapters: Dict[str, Type[BaseMosoroAdapter]] = {}

    discovered = entry_points(group=ADAPTER_ENTRY_POINT_GROUP)

    if not discovered:
        logger.debug(
            "No adapters discovered under '%s' entry point group.",
            ADAPTER_ENTRY_POINT_GROUP,
        )
        return adapters

    for ep in discovered:
        try:
            adapter_class = ep.load()
            if not isinstance(adapter_class, type) or not issubclass(
                adapter_class, BaseMosoroAdapter
            ):
                logger.warning(
                    "Entry point '%s' does not point to a BaseMosoroAdapter subclass. Skipping.",
                    ep.name,
                )
                continue

            adapters[ep.name] = adapter_class
            logger.info("Registered adapter '%s' from entry point.", ep.name)

        except Exception as e:
            logger.warning("Failed to load adapter entry point '%s': %s", ep.name, e)

    logger.info(
        "Adapter discovery complete: %d adapter(s) found via entry points.",
        len(adapters),
    )
    return adapters


def list_available_adapters() -> Dict[str, str]:
    """Return a summary of available adapters for display/debugging.

    Returns:
        Dict mapping vendor name to the fully qualified class name.
    """
    adapters = discover_adapters()
    return {name: f"{cls.__module__}.{cls.__qualname__}" for name, cls in adapters.items()}
