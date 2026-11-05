"""The binding planner: one guarded SQL step per binding."""
from __future__ import annotations

from collections.abc import Sequence

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.service.internal.emission import SqlEmitter
from kg_build_system.kernel import PlanContext, RuntimeField, Step


class BindingPlanner:
    """Plan one ``binding.<index>`` step for every blueprint binding."""

    component_id = "core"
    version = "4"
    runtime_fields: tuple[RuntimeField, ...] = ()

    def __init__(self, *, engine: SqlEmitter) -> None:
        self._engine = engine

    def plan(
        self, blueprint: GraphBlueprint, context: PlanContext,
    ) -> Sequence[Step]:
        """Return the binding steps for this compile.

        Example:
            ```python
            steps = BindingPlanner().plan(blueprint, PlanContext())
            ```
        """
        from kg_build_system.distribution.modules.core.binding.service._private.steps import (
            binding_steps,
        )
        from kg_build_system.distribution.modules.core.service._private.planning.plan import (
            core_plan,
        )

        return binding_steps(
            blueprint, core_plan(blueprint, context), engine=self._engine,
        )


__all__ = ["BindingPlanner"]
