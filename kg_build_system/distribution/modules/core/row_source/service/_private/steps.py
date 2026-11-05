"""The row-source steps the row-source planner authors."""
from __future__ import annotations

from kg_build_system.distribution.languages.data.model.internal import (
    RowSourcePlanDTO,
)
from kg_build_system.distribution.languages.data.service.internal import (
    plan_inputs,
    row_source_key,
)
from kg_build_system.distribution.model.public.artifacts import (
    CoreArtifactTypes,
)
from kg_build_system.distribution.modules.core.service._private.planning.artifacts import (
    read_input,
)
from kg_build_system.distribution.modules.core.service._private.planning.plan import (
    CorePlan,
)
from kg_build_system.distribution.service.internal.emission import SqlEmitter
from kg_build_system.kernel import Instruction, Output, Step
from .sql import row_source_sql


def row_source_step(
    plan: RowSourcePlanDTO,
    core_plan: CorePlan,
    *,
    engine: SqlEmitter,
) -> Step:
    """One step that materialises a derived row-source plan."""
    key = row_source_key(plan)
    return Step(
        component="core",
        name=f"rowsource.{key}",
        inputs=tuple(
            read_input(
                child_key,
                core_plan.projection_relations,
                core_plan.row_source_relations,
            )
            for child_key in dict.fromkeys(
                row_source_key(child) for child in plan_inputs(plan)
            )
        ),
        outputs=(Output(CoreArtifactTypes.row_source(key)),),
        instruction=Instruction(engine.kind, {
            "relation": core_plan.row_source_relations[key],
            "sql": row_source_sql(
                plan,
                core_plan.relations,
                {**core_plan.shapes, **core_plan.row_source_fields},
                engine=engine,
            ),
        }),
    )


def row_source_steps(
    core_plan: CorePlan, *, engine: SqlEmitter,
) -> tuple[Step, ...]:
    """Every row-source step, children before the plans that read them."""
    return tuple(
        row_source_step(plan, core_plan, engine=engine)
        for plan in core_plan.row_source_plans
    )


__all__ = ["row_source_step", "row_source_steps"]
