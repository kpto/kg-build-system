"""The row-source planner: derived row plans, children first."""
from __future__ import annotations

from collections.abc import Sequence

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.modules.duckdb import DuckDbSqlEmitter
from kg_build_system.kernel import PlanContext, RuntimeField, Step


class RowSourcePlanner:
    """Plan one ``rowsource.<key>`` step for every derived row-source plan."""

    component_id = "core"
    version = "4"
    runtime_fields: tuple[RuntimeField, ...] = ()

    def __init__(self, *, engine: DuckDbSqlEmitter | None = None) -> None:
        self._engine = engine

    def plan(
        self, blueprint: GraphBlueprint, context: PlanContext,
    ) -> Sequence[Step]:
        """Return the row-source steps for this compile.

        Example:
            ```python
            steps = RowSourcePlanner().plan(blueprint, PlanContext())
            ```
        """
        from kg_build_system.distribution.modules.core.service._private.planning.plan import (
            core_plan,
        )
        from kg_build_system.distribution.modules.core.row_source.service._private.steps import (
            row_source_steps,
        )

        return row_source_steps(core_plan(blueprint, context), engine=self._engine)


__all__ = ["RowSourcePlanner"]
