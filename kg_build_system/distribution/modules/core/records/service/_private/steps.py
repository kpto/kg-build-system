"""The graph-record aggregation steps the records planner authors."""
from __future__ import annotations

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.binding.model.internal.dto import (
    BindingDTO,
)
from kg_build_system.distribution.model.public.artifacts import (
    CoreArtifactTypes,
)
from kg_build_system.distribution.modules.core.service._private.planning.artifacts import (
    component_kind,
    graph_record_components,
)
from kg_build_system.kernel import (
    ArtifactPattern, Input, Instruction, InstructionKind, Output, Step,
)


def aggregation_steps(
    blueprint: GraphBlueprint, bindings: tuple[BindingDTO, ...],
) -> tuple[Step, ...]:
    """One deferred union step per component that has at least one binding."""
    steps: list[Step] = []
    for component in graph_record_components(blueprint):
        indexes = tuple(
            index
            for index, binding in enumerate(bindings)
            if binding.component == component.name
        )
        if not indexes:
            continue
        steps.append(Step(
            component="core",
            name=f"aggregate.{component.name}",
            inputs=tuple(
                Input(
                    type=ArtifactPattern(
                        CoreArtifactTypes.binding(
                            component.name, index,
                        ).key,
                    ),
                    opening_name=None,
                    declared_name=f"binding.{index}",
                )
                for index in indexes
            ),
            outputs=(Output(CoreArtifactTypes.graph_records(
                component_kind(component), component.name,
            )),),
            assembly_preference="deferred",
            instruction=Instruction(InstructionKind("aggregate", "duckdb"), {
                "relation": f"kg_graph_{component.name.lower()}",
            }),
        ))
    return tuple(steps)


__all__ = ["aggregation_steps"]
