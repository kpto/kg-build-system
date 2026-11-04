"""The distribution's feature modules.

A module combines the planners, executors, model and service it needs for one
feature. ``core`` is five planners over one shared plan; the remaining modules
own deduplication, merging, conflict validation and the execution targets.
"""
from __future__ import annotations

__all__: list[str] = []
