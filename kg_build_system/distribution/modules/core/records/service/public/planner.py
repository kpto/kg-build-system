"""The records planner: one aggregate step per bound component."""
from __future__ import annotations

from collections.abc import Sequence

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.service.internal.emission import SqlEmitter
from kg_build_system.kernel import PlanContext, RuntimeField, Step


class RecordsPlanner:
    """Plan one ``aggregate.<component>`` step for every bound component."""

    component_id = "core"
    version = "4"
    runtime_fields: tuple[RuntimeField, ...] = ()

    def __init__(self, *, engine: SqlEmitter) -> None:
        self._engine = engine

    def plan(
        self, blueprint: GraphBlueprint, context: PlanContext,
    ) -> Sequence[Step]:
        """Return the graph-record aggregation steps for this compile.

        Example:
            ```python
            steps = RecordsPlanner().plan(blueprint, PlanContext())
            ```
        """
        from kg_build_system.distribution.modules.core.service._private.planning.plan import (
            core_plan,
        )
        from kg_build_system.distribution.modules.core.records.service._private.steps import (
            aggregation_steps,
        )

        plan = core_plan(blueprint, context)
        return aggregation_steps(blueprint, plan.bindings)


__all__ = ["RecordsPlanner"]
