"""Thin re-export of the deduplication planner implementation."""
from __future__ import annotations

from .._private.planner import DeduplicationPlanner

__all__ = ["DeduplicationPlanner"]
