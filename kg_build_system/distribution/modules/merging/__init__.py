"""The merging planner: fold compatible same-key facts into one record."""
from __future__ import annotations

from .model.public import MergingConfiguration
from .service.public import MergingPlanner

__all__ = ["MergingConfiguration", "MergingPlanner"]
