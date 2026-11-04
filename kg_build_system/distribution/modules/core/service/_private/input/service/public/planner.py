"""The input planner: physical sources as logical table relations."""
from __future__ import annotations

from collections.abc import Sequence

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.modules.duckdb import DuckDbSqlEmitter
from kg_build_system.kernel import PlanContext, RuntimeField, Step


class InputPlanner:
    """Plan one ``table.<name>`` step for every source the build reads."""

    component_id = "core"
    version = "4"
    runtime_fields: tuple[RuntimeField, ...] = ()

    def __init__(self, *, engine: DuckDbSqlEmitter | None = None) -> None:
        self._engine = engine

    def plan(
        self, blueprint: GraphBlueprint, context: PlanContext,
    ) -> Sequence[Step]:
        """Return the source steps for this compile.

        Example:
            ```python
            steps = InputPlanner().plan(blueprint, PlanContext())
            ```
        """
        from kg_build_system.distribution.modules.core.service._private.input.service._private.steps import (
            source_steps,
        )
        from kg_build_system.distribution.modules.core.service._private.planning.plan import (
            core_plan,
        )

        return source_steps(blueprint, core_plan(blueprint, context))


__all__ = ["InputPlanner"]
