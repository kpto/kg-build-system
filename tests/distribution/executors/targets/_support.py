"""Small plan and blueprint fixtures shared by the target tests."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from kg_build_system.distribution.languages.data.model.internal import DataPartDTO
from kg_build_system.distribution.languages.topology.model.internal.dto import (
    GraphPartDTO,
    NodeDTO,
    PropertyDTO,
)
from kg_build_system.kernel import ArtifactType, Component, Connection
from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO


def node(name: str, *properties: str) -> NodeDTO:
    """A node component with string properties, in its own label."""
    return NodeDTO(
        name=name,
        labels=(name,),
        properties=tuple(
            PropertyDTO(property_name, UnitTypeDTO("str"))
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
    return ArtifactType("core", f"graph.node.{component}")


def output_id(component: str, step: str, output: str) -> str:
    """The whole-workflow identity of one output opening."""
    return f"{component}.{step}.{output}"


def input_id(component: str, step: str, input_name: str) -> str:
    """The whole-workflow identity of one consumed input opening."""
    return f"{component}.{step}.{input_name}"


def connection(
    consumer: tuple[str, str, str],
    producer: tuple[str, str, str],
) -> Connection:
    """Connect one consumer input name to one producer output name."""
    return Connection(
        input_id(*consumer),
        output_id(*producer),
    )


def component(component_id: str, version: str, runtime_fields: Any = ()) -> Component:
    """One plan component declaration."""
    return Component(component_id, version, tuple(runtime_fields))
