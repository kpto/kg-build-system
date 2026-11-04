"""The graph-record aggregation steps the records planner authors."""
from __future__ import annotations

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.binding.model.internal.dto import (
    BindingDTO,
)
from kg_build_system.distribution.modules.core.service._private.planning.artifacts import (
    CoreArtifactTypes,
    component_kind,
    graph_record_components,
)
from kg_build_system.kernel import Input, Instruction, Output, Step


def aggregation_steps(
    blueprint: GraphBlueprint, bindings: tuple[BindingDTO, ...],
) -> tuple[Step, ...]:
    """One deferred union step per component that has at least one binding."""
    steps: list[Step] = []
    for component in graph_record_components(blueprint):
        identities = tuple(
            f"{binding.component}.{index}"
            for index, binding in enumerate(bindings)
            if binding.component == component.name
        )
        if not identities:
            continue
        name = f"aggregate.{component.name}"
        steps.append(Step(
            component="core",
            name=name,
            inputs=tuple(
                Input(
                    type=CoreArtifactTypes.binding(identity),
                    name=None,
                    input_name=f"binding.{identity}",
                )
                for identity in identities
            ),
            outputs=(Output(CoreArtifactTypes.graph_records(
                component_kind(component), component.name,
            )),),
            assembly_preference="deferred",
            instruction=Instruction(("aggregate", "duckdb"), {
                "relation": f"kg_graph_{component.name.lower()}",
            }),
        ))
    return tuple(steps)


__all__ = ["aggregation_steps"]
