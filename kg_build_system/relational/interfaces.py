"""Framework-internal interface of the relational planning domain.

The planner produces engine-neutral plans. An engine lowers those plans, so the
protocols here state only what a plan lowerer is asked for; they name no SQL type
and no engine.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, TypeVar

from ..table.ir import RowSourcePlanIR
from .ir import ExpandIR, FilterIR, RelationPlanIR, ScanIR
from .planner import expansion_scope, lower_product

ResultT = TypeVar("ResultT", covariant=True)


class RelationPlanLowerer(Protocol[ResultT]):
    """Render one planned relational product for an execution engine."""

    def lower_plan(self, plan: RelationPlanIR) -> ResultT: ...


class RowSourcePlanLowerer(Protocol[ResultT]):
    """Render one row-source plan over relations the caller already named."""

    def lower_row_source(
        self,
        plan: RowSourcePlanIR,
        relations: Mapping[str, str],
        shapes: Mapping[str, tuple[Any, ...]],
    ) -> ResultT: ...


class PlanLowerer(RelationPlanLowerer[ResultT], RowSourcePlanLowerer[ResultT], Protocol[ResultT]):
    """The complete lowering surface an engine offers for neutral plans."""


__all__ = [
    "ExpandIR",
    "FilterIR",
    "PlanLowerer",
    "RelationPlanIR",
    "RelationPlanLowerer",
    "RowSourcePlanIR",
    "RowSourcePlanLowerer",
    "ScanIR",
    "expansion_scope",
    "lower_product",
]
