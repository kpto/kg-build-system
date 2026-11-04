"""The binding steps the binding planner authors."""
from __future__ import annotations

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.binding.model.internal.dto import (
    BindingDTO,
)
from kg_build_system.distribution.modules.core.service._private.planning.artifacts import (
    CoreArtifactTypes,
    read_input,
)
from kg_build_system.distribution.modules.core.service._private.planning.emission import (
    binding_sources,
)
from kg_build_system.distribution.modules.core.service._private.planning.plan import (
    CorePlan,
)
from kg_build_system.distribution.modules.duckdb.service.internal.emitters import (
    DuckDbSqlEmitter,
)
from kg_build_system.kernel import Instruction, Output, Step
from .sql import binding_sql


def binding_identity(binding: BindingDTO, index: int) -> str:
    """The graph-name identity of one binding in a contribution."""
    return f"{binding.component}.{index}"


def binding_step(
    blueprint: GraphBlueprint,
    binding: BindingDTO,
    index: int,
    core_plan: CorePlan,
    *,
    engine: DuckDbSqlEmitter | None = None,
) -> Step:
    """One step that materialises one binding's rows."""
    identity = binding_identity(binding, index)
    binding_sql_text = binding_sql(
        blueprint, core_plan.relations, binding, engine=engine,
    )
    return Step(
        component="core",
        name=f"binding.{index}",
        inputs=tuple(
            read_input(
                name,
                core_plan.projection_relations,
                core_plan.row_source_relations,
            )
            for name in sorted(binding_sources(binding))
        ),
        outputs=(Output(CoreArtifactTypes.binding(identity)),),
        instruction=Instruction(("sql", "duckdb"), {
            "relation": f"kg_binding_{index}",
            "sql": (
                f"SELECT *, '{identity}' AS _kg_binding_symbol "
                f"FROM ({binding_sql_text})"
            ),
        }),
    )


def binding_steps(
    blueprint: GraphBlueprint,
    core_plan: CorePlan,
    *,
    engine: DuckDbSqlEmitter | None = None,
) -> tuple[Step, ...]:
    """Every binding step, in blueprint binding order."""
    return tuple(
        binding_step(blueprint, binding, index, core_plan, engine=engine)
        for index, binding in enumerate(core_plan.bindings)
    )


__all__ = ["binding_identity", "binding_step", "binding_steps"]
