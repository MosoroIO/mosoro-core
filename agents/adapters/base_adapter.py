"""
Mosoro Base Adapter — Backward Compatibility Shim
===================================================

The canonical ``BaseMosoroAdapter`` class now lives in ``mosoro_core.base_adapter``.
This file re-exports it for backward compatibility with existing code that imports::

    from agents.adapters.base_adapter import BaseMosoroAdapter

New code should import directly from the package::

    from mosoro_core.base_adapter import BaseMosoroAdapter
"""

from mosoro_core.base_adapter import BaseMosoroAdapter

__all__ = ["BaseMosoroAdapter"]
