"""Small plan and blueprint fixtures shared by the target tests."""
from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import Any

from kg_build_system.distribution.languages.data.model.internal import DataPartDTO
from kg_build_system.distribution.languages.topology.model.internal.dto import (
    GraphPartDTO,
    NodeDTO,
    PropertyDTO,
)
from kg_build_system.distribution.model.public.artifacts import CoreArtifactTypes
from kg_build_system.distribution.model.public.refs import (
    NodeRef, PropertyRef,
)
from kg_build_system.kernel import (
    ArtifactType, Component, Connection, Key, OpeningDirection, OpeningId, Step,
    step_id,
)
from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO


def node(name: str, *properties: str) -> NodeDTO:
    """A node component with string properties, in its own label."""
    return NodeDTO(
        name=name,
        labels=(name,),
        properties=tuple(
            PropertyDTO(
                property_name,
                UnitTypeDTO("str"),
                PropertyRef(
                    "topology", Key((f"{name}.{property_name}",)),
                ),
            )
            for property_name in properties
        ),
    )


def bound_blueprint(*components: NodeDTO) -> Any:
    """A blueprint-shaped value with one binding per node component."""
    graph = GraphPartDTO(nodes=components, edges=())
    data = DataPartDTO(
        structs=(), relations=(), projections=(), sources=(),
    )
    bindings = tuple(
        SimpleNamespace(
            component=component.name,
            debug_name=component.name.lower(),
            source_node=None,
            target_node=None,
        )
        for component in components
    )
    return SimpleNamespace(graph=graph, data=data, bindings=bindings)


def record_type(component: str) -> ArtifactType:
    """The core graph-record artifact type for one node component."""
    return CoreArtifactTypes.graph_records("node", component)


def opening(
    step: Step, direction: OpeningDirection, name: str,
) -> OpeningId:
    """The typed opening of one manually built step."""
    return OpeningId(step_id(step), direction, Key((name,)))


def resolve_inputs(step: Step) -> Step:
    """Give a planned step one concrete opening per declared input name."""
    return replace(
        step,
        inputs=tuple(
            replace(taken, opening_name=Key((taken.declared_name,)))
            for taken in step.inputs
        ),
    )


def connection(input: OpeningId, output: OpeningId) -> Connection:
    """Connect one typed input opening to one typed output opening."""
    return Connection(input=input, output=output)


def component(component_id: str, version: str, runtime_fields: Any = ()) -> Component:
    """One plan component declaration."""
    return Component(component_id, version, tuple(runtime_fields))
