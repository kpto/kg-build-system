"""Cross-layer validation of an assembled graph blueprint."""
from __future__ import annotations

from typing import Any

from kg_build_system.distribution.languages.binding.model.internal.dto.blueprint_dto import (
    EdgeBindingDTO, NodeBindingDTO,
)
from kg_build_system.distribution.languages.data.model.internal.dto.blueprint_dto import (
    DataPartDTO,
)
from kg_build_system.distribution.languages.topology.model.internal.dto.blueprint_dto import (
    EdgeDTO, NodeDTO,
)
from kg_build_system.distribution.model.public.refs import (
    EdgeRef, FieldRef, NodeRef, PropertyRef, RelationRef,
)
from kg_build_system.kernel import Key
from ...model.public import GraphBlueprint


def _components(graph: Any) -> tuple[Any, ...]:
    nodes = tuple(getattr(graph, "nodes", ()))
    edges = tuple(getattr(graph, "edges", ()))
    if nodes or edges:
        return (*nodes, *edges)
    return tuple(getattr(graph, "components", ()))


def _name(value: Any) -> str:
    name = getattr(value, "name", None)
    if not isinstance(name, str) or not name:
        raise ValueError("graph components, relations and sources require a name")
    return name


def _relations(data: DataPartDTO) -> tuple[Any, ...]:
    relations = getattr(data, "relations", None)
    if relations is not None:
        return tuple(relations)
    return tuple(getattr(data, "tables", ()))


def _node_ref(name: str) -> NodeRef:
    return NodeRef("topology", Key((name,)))


def _edge_ref(name: str) -> EdgeRef:
    return EdgeRef("topology", Key((name,)))


def _relation_ref(name: str) -> RelationRef:
    return RelationRef("data", Key((name,)))


def _field_ref(owner: str, name: str) -> FieldRef:
    return FieldRef("data", Key((f"{owner}.{name}",)))


def _property_ref(owner: str, name: str) -> PropertyRef:
    return PropertyRef("topology", Key((f"{owner}.{name}",)))


def _source_relation(source: Any) -> RelationRef:
    relation = getattr(source, "relation", None)
    if not isinstance(relation, RelationRef):
        raise ValueError("sources require the relation reference they bind")
    return relation


def _source_name(source: Any) -> str:
    name = getattr(source, "name", None)
    if isinstance(name, str) and name:
        return name
    return _source_relation(source).name


def _binding_component(binding: Any) -> str:
    component = getattr(binding, "component", None)
    if not isinstance(component, str) or not component:
        raise ValueError("bindings require a target component name")
    return component


def _binding_target(binding: Any) -> Any:
    if isinstance(binding, NodeBindingDTO):
        return binding.node
    if isinstance(binding, EdgeBindingDTO):
        return binding.edge
    raise ValueError("bindings require a node or edge reference")


def _validate_columns(
    owner: Any, ref_for: Any, context: str,
) -> None:
    for column in owner.columns:
        expected = ref_for(owner.name, column.name)
        if column.ref != expected:
            raise ValueError(
                f"{context} {owner.name!r} column {column.name!r} "
                f"does not carry {expected}"
            )


def _validate_properties(component: Any) -> None:
    for prop in component.properties:
        expected = _property_ref(component.name, prop.name)
        if prop.ref != expected:
            raise ValueError(
                f"component {component.name!r} property {prop.name!r} "
                f"does not carry {expected}"
            )


def validate_blueprint(blueprint: GraphBlueprint) -> None:
    """Reject a blueprint with colliding names or dangling references.

    The checks are reference-based: every endpoint, parent, property, field,
    source and binding must carry the role reference whose language and key name
    an existing declaration. Names are only used for the messages.
    """
    components = _components(blueprint.graph)
    names = tuple(_name(item) for item in components)
    if len(names) != len(set(names)):
        raise ValueError("component names must be unique")
    nodes = {_node_ref(item.name) for item in blueprint.graph.nodes}
    edges = {_edge_ref(item.name) for item in blueprint.graph.edges}
    known = nodes | edges

    for item in components:
        _validate_properties(item)
        if isinstance(item, EdgeDTO):
            for endpoint in (item.source, item.target):
                if endpoint not in nodes:
                    raise ValueError(
                        f"edge {item.name!r} has an unknown endpoint "
                        f"{endpoint.name!r}"
                    )
        parent = getattr(item, "parent", None)
        if parent is not None:
            allowed = nodes if isinstance(item, NodeDTO) else edges
            if parent not in allowed:
                raise ValueError(
                    f"component {item.name!r} has an unknown parent "
                    f"{parent.name!r}"
                )

    relations = {_relation_ref(item.name) for item in blueprint.data.relations}
    projections = {
        _relation_ref(item.name) for item in blueprint.data.projections
    }
    for relation in blueprint.data.relations:
        _validate_columns(relation, _field_ref, "relation")
    for projection in blueprint.data.projections:
        _validate_columns(projection, _field_ref, "projection")

    for binding in blueprint.bindings:
        target = _binding_target(binding)
        if target not in known:
            raise ValueError(
                f"binding targets an unknown component {binding.component!r}"
            )
        if isinstance(binding, NodeBindingDTO) and target not in nodes:
            raise ValueError(
                f"node binding targets an unknown node {binding.component!r}"
            )
        if isinstance(binding, EdgeBindingDTO) and target not in edges:
            raise ValueError(
                f"edge binding targets an unknown edge {binding.component!r}"
            )
        if isinstance(binding, EdgeBindingDTO):
            for endpoint in (binding.source_node, binding.target_node):
                if endpoint is not None and endpoint not in nodes:
                    raise ValueError(
                        f"edge binding targets an unknown endpoint "
                        f"{endpoint.name!r}"
                    )

    source_names: list[str] = []
    for source in blueprint.sources:
        source_names.append(_source_name(source))
        relation = _source_relation(source)
        if relation not in relations:
            if relation in projections:
                raise ValueError(
                    f"source {source_names[-1]!r} names a projection "
                    f"{relation.name!r}, not a relation"
                )
            raise ValueError(
                f"source {source_names[-1]!r} names an unknown relation "
                f"{relation.name!r}"
            )
    if len(source_names) != len(set(source_names)):
        raise ValueError("source names must be unique")


__all__ = ["validate_blueprint"]
