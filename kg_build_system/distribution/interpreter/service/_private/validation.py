"""Cross-layer validation of an assembled graph blueprint."""
from __future__ import annotations

from typing import Any

from kg_build_system.distribution.languages.asset.model.internal.dto import (
    AssetPartDTO,
)
from kg_build_system.distribution.languages.binding.model.internal.dto.blueprint_dto import (
    EdgeBindingDTO, NodeBindingDTO,
)
from kg_build_system.distribution.languages.data.model.internal.dto.blueprint_dto import (
    DataPartDTO,
)
from kg_build_system.distribution.languages.data.service.internal import (
    plan_scan_sources,
)
from kg_build_system.distribution.languages.graph.model.internal.dto import (
    GraphDeclarationDTO,
)
from kg_build_system.distribution.languages.meaning.model.internal import (
    PurposeDTO,
    MeaningDTO,
)
from kg_build_system.distribution.languages.topology.model.internal.dto.blueprint_dto import (
    EdgeDTO, NodeDTO,
)
from kg_build_system.distribution.model.public.refs import (
    AssetRef, EdgeRef, FieldRef, NodeRef, PropertyRef, RelationRef,
)
from kg_build_system.kernel import Key
from ...model.public import GraphBlueprint


def _validate_graph_declaration(blueprint: GraphBlueprint) -> None:
    declaration = blueprint.graph_declaration
    if declaration is None:
        return
    if not isinstance(declaration, GraphDeclarationDTO):
        raise ValueError("the graph declaration must be a GraphDeclarationDTO")
    meaning = declaration.meaning
    if not isinstance(meaning, MeaningDTO):
        raise ValueError(
            "a graph declaration requires a Meaning with a purpose"
        )
    if not isinstance(meaning.purpose, PurposeDTO):
        raise ValueError(
            "a graph declaration requires a Meaning with a purpose"
        )
    if not meaning.purpose.text:
        raise ValueError("the graph declaration purpose must be non-empty")


def _declaration_meaning(blueprint: GraphBlueprint) -> tuple[Any, ...]:
    """Return every attached declaration meaning value in the blueprint."""
    values: list[Any] = []
    for component in _components(blueprint.graph):
        meaning = getattr(component, "meaning", None)
        if meaning is not None:
            values.append(meaning)
        for prop in getattr(component, "properties", ()):
            if prop.meaning is not None:
                values.append(prop.meaning)
    for owner in (
        *blueprint.data.structs,
        *blueprint.data.source_relations,
        *blueprint.data.derived_relations,
    ):
        if owner.meaning is not None:
            values.append(owner.meaning)
        for column in owner.columns:
            if column.meaning is not None:
                values.append(column.meaning)
    for asset in blueprint.assets.assets:
        if asset.meaning is not None:
            values.append(asset.meaning)
    for binding in blueprint.bindings:
        if binding.meaning is not None:
            values.append(binding.meaning)
    return tuple(values)


def _graph_local_meaning(blueprint: GraphBlueprint) -> tuple[Any, ...]:
    """Return the meanings that narrow the graph purpose.

    Only topology declarations sit under the graph purpose. A relation purpose
    is domain-level and stands without one.
    """
    values: list[Any] = []
    for component in _components(blueprint.graph):
        meaning = getattr(component, "meaning", None)
        if meaning is not None:
            values.append(meaning)
        for prop in getattr(component, "properties", ()):
            if prop.meaning is not None:
                values.append(prop.meaning)
    return tuple(values)


def _validate_purposes(blueprint: GraphBlueprint) -> None:
    """Reject a graph-local purpose without a graph purpose."""
    declaration = blueprint.graph_declaration
    root = (
        declaration.meaning.purpose
        if declaration is not None
        else None
    )
    for meaning in _declaration_meaning(blueprint):
        if not isinstance(meaning, MeaningDTO):
            raise ValueError(
                "a declaration meaning must be a Meaning value"
            )
    for meaning in _graph_local_meaning(blueprint):
        if meaning.purpose is not None and root is None:
            raise ValueError(
                "a local purpose requires a graph declaration with a purpose"
            )


def _components(graph: Any) -> tuple[Any, ...]:
    nodes = tuple(getattr(graph, "nodes", ()))
    edges = tuple(getattr(graph, "edges", ()))
    if nodes or edges:
        return (*nodes, *edges)
    return tuple(getattr(graph, "components", ()))


def _name(value: Any) -> str:
    name = getattr(value, "name", None)
    if not isinstance(name, str) or not name:
        raise ValueError("graph components, relations and assets require a name")
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


def _asset_ref(name: str) -> AssetRef:
    return AssetRef("asset", Key((name,)))


def _field_ref(owner: str, name: str) -> FieldRef:
    return FieldRef("data", Key((f"{owner}.{name}",)))


def _property_ref(owner: str, name: str) -> PropertyRef:
    return PropertyRef("topology", Key((f"{owner}.{name}",)))


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


def _validate_assets(assets: AssetPartDTO) -> set[AssetRef]:
    names = tuple(_name(asset) for asset in assets.assets)
    if len(names) != len(set(names)):
        raise ValueError("asset names must be unique")
    return {_asset_ref(name) for name in names}


def validate_blueprint(blueprint: GraphBlueprint) -> None:
    """Reject a blueprint with colliding names or dangling references.

    The checks are reference-based: every endpoint, parent, property, field,
    relation asset and binding must carry the role reference whose language and
    key name an existing declaration. A graph declaration, when present, must
    carry a ``Meaning`` value with a purpose. A local declaration purpose is
    refused when the project declares no graph purpose. Names are only used for
    the messages.
    """
    _validate_graph_declaration(blueprint)
    _validate_purposes(blueprint)
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

    assets = _validate_assets(blueprint.assets)
    for relation in blueprint.data.source_relations:
        if relation.asset is None:
            raise ValueError(
                f"relation {relation.name!r} must name its logical asset"
            )
        if relation.asset not in assets:
            raise ValueError(
                f"relation {relation.name!r} names an unknown asset "
                f"{relation.asset.name!r}"
            )
    for relation in blueprint.data.source_relations:
        _validate_columns(relation, _field_ref, "relation")
    for derived_relation in blueprint.data.derived_relations:
        _validate_columns(derived_relation, _field_ref, "derived relation")
    internal = {
        relation.name
        for relation in blueprint.data.derived_relations
        if relation.visibility == "internal"
    }

    for binding in blueprint.bindings:
        if binding.rows is not None and internal.intersection(
            plan_scan_sources(binding.rows)
        ):
            raise ValueError(
                "rows must not read a stage; bind the derived relation that "
                "publishes the stage"
            )
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


__all__ = ["validate_blueprint"]
