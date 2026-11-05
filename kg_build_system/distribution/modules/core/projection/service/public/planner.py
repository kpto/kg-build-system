"""The projection planner: declared projections, dependency order."""
from __future__ import annotations

from collections.abc import Sequence

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.modules.duckdb import DuckDbSqlEmitter
from kg_build_system.kernel import PlanContext, RuntimeField, Step


class ProjectionPlanner:
    """Plan one ``projection.<name>`` step for every declared projection."""

    component_id = "core"
    version = "4"
    runtime_fields: tuple[RuntimeField, ...] = ()

    def __init__(self, *, engine: DuckDbSqlEmitter | None = None) -> None:
        self._engine = engine

    def plan(
        self, blueprint: GraphBlueprint, context: PlanContext,
    ) -> Sequence[Step]:
        """Return the projection steps for this compile.

        Example:
            ```python
            steps = ProjectionPlanner().plan(blueprint, PlanContext())
            ```
        """
        from kg_build_system.distribution.modules.core.service._private.planning.plan import (
            core_plan,
        )
        from kg_build_system.distribution.modules.core.projection.service._private.steps import (
            projection_steps,
        )

        return projection_steps(core_plan(blueprint, context), engine=self._engine)


__all__ = ["ProjectionPlanner"]
