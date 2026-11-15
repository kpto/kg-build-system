"""The derived-relation planner: declared relations, dependency order."""
from __future__ import annotations

from collections.abc import Sequence

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.service.internal.emission import SqlEmitter
from kg_build_system.kernel import PlanContext, RuntimeField, Step


class DerivedRelationPlanner:
    """Plan one ``projection.<name>`` step for every derived relation."""

    component_id = "core"
    version = "4"
    runtime_fields: tuple[RuntimeField, ...] = ()

    def __init__(self, *, engine: SqlEmitter) -> None:
        self._engine = engine

    def plan(
        self, blueprint: GraphBlueprint, context: PlanContext,
    ) -> Sequence[Step]:
        """Return the derived-relation steps for this compile.

        Example:
            ```python
            steps = DerivedRelationPlanner().plan(blueprint, PlanContext())
            ```
        """
        from kg_build_system.distribution.modules.core.service._private.planning.plan import (
            core_plan,
        )
        from kg_build_system.distribution.modules.core.derived_relation.service._private.steps import (
            derived_relation_steps,
        )

        return derived_relation_steps(
            core_plan(blueprint, context), engine=self._engine,
        )


__all__ = ["DerivedRelationPlanner"]
