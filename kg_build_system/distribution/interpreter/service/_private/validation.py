"""Cross-layer validation of an assembled graph blueprint."""
from __future__ import annotations

from typing import Any

from kg_build_system.distribution.languages.binding.model.internal.dto.blueprint_dto import EdgeBindingDTO
from kg_build_system.distribution.languages.data.model.internal.dto.blueprint_dto import DataPartDTO
from kg_build_system.distribution.languages.topology.model.internal.dto.blueprint_dto import EdgeDTO
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


def _source_relation(source: Any) -> str:
    for attribute in ("table", "relation"):
        value = getattr(source, attribute, None)
        if isinstance(value, str) and value:
            return value
    raise ValueError("sources require the name of the relation they bind")


def _source_name(source: Any) -> str:
    name = getattr(source, "name", None)
    if isinstance(name, str) and name:
        return name
    return _source_relation(source)


def _binding_component(binding: Any) -> str:
    component = getattr(binding, "component", None)
    if not isinstance(component, str) or not component:
        raise ValueError("bindings require a target component name")
    return component


def _binding_endpoint(binding: Any, *names: str) -> str | None:
    for name in names:
        value = getattr(binding, name, None)
        if isinstance(value, str) and value:
            return value
    return None


def validate_blueprint(blueprint: GraphBlueprint) -> None:
    """Reject a blueprint with colliding names or dangling references.

    The checks are structural and layer-neutral: component names are unique,
    edge endpoints and component parents name existing components, every
    binding targets an existing component, every physical source names an
    existing relation and source names are unique.
    """
    components = _components(blueprint.graph)
    names = tuple(_name(item) for item in components)
    if len(names) != len(set(names)):
        raise ValueError("component names must be unique")
    known = set(names)

    for item in components:
        if isinstance(item, EdgeDTO):
            for endpoint in (item.source, item.target):
                if endpoint not in known:
                    raise ValueError(
                        f"edge {item.name!r} has an unknown endpoint {endpoint!r}"
                    )
        parent = getattr(item, "parent", None)
        if parent is not None and parent not in known:
            raise ValueError(
                f"component {item.name!r} has an unknown parent {parent!r}"
            )

    component_names = known
    for binding in blueprint.bindings:
        component = _binding_component(binding)
        if component not in component_names:
            raise ValueError(
                f"binding targets an unknown component {component!r}"
            )
        if isinstance(binding, EdgeBindingDTO):
            for endpoint in (
                _binding_endpoint(binding, "source_node", "source"),
                _binding_endpoint(binding, "target_node", "target"),
            ):
                if endpoint is not None and endpoint not in component_names:
                    raise ValueError(
                        f"edge binding targets an unknown endpoint {endpoint!r}"
                    )

    relation_names = {_name(item) for item in _relations(blueprint.data)}
    source_names: list[str] = []
    for source in blueprint.sources:
        source_names.append(_source_name(source))
        relation = _source_relation(source)
        if relation not in relation_names:
            raise ValueError(
                f"source {source_names[-1]!r} names an unknown relation {relation!r}"
            )
    if len(source_names) != len(set(source_names)):
        raise ValueError("source names must be unique")


__all__ = ["validate_blueprint"]
