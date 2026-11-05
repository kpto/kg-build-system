"""The projection steps the projection planner authors."""
from __future__ import annotations

from kg_build_system.distribution.languages.data.model.internal import (
    ProjectionDTO,
)
from kg_build_system.distribution.model.public.artifacts import (
    CoreArtifactTypes,
)
from kg_build_system.distribution.modules.core.service._private.planning.artifacts import (
    read_input,
)
from kg_build_system.distribution.modules.core.service._private.planning.emission import (
    projection_sources,
)
from kg_build_system.distribution.modules.core.service._private.planning.plan import (
    CorePlan,
)
from kg_build_system.distribution.service.internal.emission import SqlEmitter
from kg_build_system.kernel import Instruction, Output, Step
from .sql import projection_sql


def projection_step(
    core_plan: CorePlan,
    projection: ProjectionDTO,
    *,
    engine: SqlEmitter,
) -> Step:
    """One step that materialises a declared projection."""
    return Step(
        component="core",
        name=f"projection.{projection.name}",
        inputs=tuple(
            read_input(
                name,
                core_plan.projection_relations,
                core_plan.row_source_relations,
            )
            for name in sorted(projection_sources(projection))
        ),
        outputs=(Output(CoreArtifactTypes.projection(projection.name)),),
        instruction=Instruction(engine.kind, {
            "relation": core_plan.projection_relations[projection.name],
            "sql": projection_sql(
                core_plan.relations, projection, engine=engine,
                shapes={**core_plan.shapes, **core_plan.row_source_fields},
            ),
        }),
    )


def projection_steps(
    core_plan: CorePlan, *, engine: SqlEmitter,
) -> tuple[Step, ...]:
    """Every projection step, in dependency order."""
    return tuple(
        projection_step(core_plan, projection, engine=engine)
        for projection in core_plan.projections
    )


__all__ = ["projection_step", "projection_steps"]
