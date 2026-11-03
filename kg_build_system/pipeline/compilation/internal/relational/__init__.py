"""Engine-neutral relation plans and planning.

A module compiler produces a :class:`RelationPlan`; an instruction emitter turns
that plan into an engine-specific instruction. The plan includes no SQL and names
no engine.
"""
from __future__ import annotations

from .model import Expand, Filter, RelationPlan, Scan
from .planner import expansion_scope, plan_product

__all__ = [
    "Expand",
    "Filter",
    "RelationPlan",
    "Scan",
    "expansion_scope",
    "plan_product",
]
