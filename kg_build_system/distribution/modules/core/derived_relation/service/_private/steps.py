"""The derived-relation steps the derived-relation planner authors."""
from __future__ import annotations

from kg_build_system.distribution.languages.data.model.internal import (
    DerivedRelationDTO,
)
from kg_build_system.distribution.model.public.artifacts import (
    CoreArtifactTypes,
)
from kg_build_system.distribution.modules.core.service._private.planning.artifacts import (
    read_input,
)
from kg_build_system.distribution.modules.core.service._private.planning.emission import (
    derived_relation_sources,
)
from kg_build_system.distribution.modules.core.service._private.planning.plan import (
    CorePlan,
)
from kg_build_system.distribution.service.internal.emission import SqlEmitter
from kg_build_system.kernel import Instruction, Output, Step
from .sql import derived_relation_sql


def derived_relation_step(
    core_plan: CorePlan,
    derived_relation: DerivedRelationDTO,
    *,
    engine: SqlEmitter,
) -> Step:
    """One step that materialises a declared derived relation."""
    return Step(
        component="core",
        name=f"projection.{derived_relation.name}",
        inputs=tuple(
            read_input(
                name,
                core_plan.derived_relations,
                core_plan.row_source_relations,
            )
            for name in sorted(derived_relation_sources(derived_relation))
        ),
        outputs=(
            Output(CoreArtifactTypes.derived_relation(derived_relation.name)),
        ),
        instruction=Instruction(engine.kind, {
            "relation": core_plan.derived_relations[derived_relation.name],
            "sql": derived_relation_sql(
                core_plan.relations, derived_relation, engine=engine,
                shapes={**core_plan.shapes, **core_plan.row_source_fields},
            ),
        }),
    )


def derived_relation_steps(
    core_plan: CorePlan, *, engine: SqlEmitter,
) -> tuple[Step, ...]:
    """Every derived-relation step, in dependency order."""
    return tuple(
        derived_relation_step(core_plan, derived_relation, engine=engine)
        for derived_relation in core_plan.derived_relation_dtos
    )


__all__ = ["derived_relation_step", "derived_relation_steps"]
