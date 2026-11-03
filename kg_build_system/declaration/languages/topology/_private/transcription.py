"""Transcribe topology declarations into the topology blueprint DTO."""
from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from typing import Any

from kg_build_system.declaration.foundations.annotations.internal import (
    Annotation,
    AnnotationDTO,
    EdgeLabel,
    NodeLabel,
    annotation_payload,
)
from kg_build_system.kernel import Namespace
from kg_build_system.kernel.internal.types import type_to_dto

from ..internal.dto.blueprint_dto import (
    EdgeDTO, GraphPartDTO, NodeDTO, PropertyDTO,
)
from ..internal.model.metadata import ComponentMetadata
from .metadata import component_kind, metadata_for


def _labels_and_annotations(
    kind: str, annotations: Sequence[Annotation],
) -> tuple[tuple[str, ...], tuple[AnnotationDTO, ...]]:
    expected = NodeLabel if kind == "node" else EdgeLabel
    opposite = EdgeLabel if kind == "node" else NodeLabel
    labels: list[str] = []
    kept: list[AnnotationDTO] = []
    for annotation in annotations:
        namespace, annotation_id, arguments = annotation_payload(annotation)
        if (
            namespace == expected.namespace
            and annotation_id == expected.annotation_id
        ):
            label = arguments.get("label")
            if not isinstance(label, str) or not label:
                raise ValueError(
                    f"{expected.__name__} must carry a non-empty string label"
                )
            labels.append(label)
            continue
        if (
            namespace == opposite.namespace
            and annotation_id == opposite.annotation_id
        ):
            raise ValueError(
                f"a {kind} component cannot carry a "
                f"{opposite.__name__} annotation"
            )
        kept.append(AnnotationDTO(namespace, annotation_id, arguments))
    if len(labels) > 1:
        raise ValueError(f"a {kind} component carries at most one label")
    return tuple(labels), tuple(kept)


def _property_dto(value: Any) -> PropertyDTO:
    annotations: list[AnnotationDTO] = []
    for annotation in value.annotations:
        namespace, annotation_id, arguments = annotation_payload(annotation)
        annotations.append(
            AnnotationDTO(namespace, annotation_id, arguments)
        )
    return PropertyDTO(
        name=value.name,
        logical_type=type_to_dto(value.logical_type),
        description=value.description,
        annotations=tuple(annotations),
    )


def _component_metadata(declaration: type[Any]) -> ComponentMetadata:
    metadata = metadata_for(declaration)
    if metadata is None:
        name = getattr(declaration, "__name__", repr(declaration))
        raise TypeError(f"{name} is not a graph-visible node or edge component")
    return metadata


def _declared_class(value: object) -> type[Any] | None:
    """The topology declaration a namespace value names, if any."""
    candidates = [value]
    if not isinstance(value, type):
        candidates.extend(
            getattr(value, attribute, None)
            for attribute in ("target", "source_node", "target_node")
        )
    for candidate in candidates:
        if isinstance(candidate, type) and component_kind(candidate) is not None:
            return candidate
    return None


def _component_closure(values: Sequence[object]) -> tuple[type[Any], ...]:
    """Collect named components plus the parents and endpoints they use."""
    pending: deque[type[Any]] = deque(
        declaration
        for value in values
        if (declaration := _declared_class(value)) is not None
    )
    seen: set[type[Any]] = set()
    result: list[type[Any]] = []
    while pending:
        declaration = pending.popleft()
        if declaration in seen:
            continue
        metadata = metadata_for(declaration)
        if metadata is None:
            continue
        seen.add(declaration)
        result.append(declaration)
        pending.extend(
            item for item in (metadata.parent, metadata.source, metadata.target)
            if item is not None
        )
    return tuple(result)


def _edges_of(
    declarations: Sequence[type[Any]],
) -> dict[str, EdgeDTO]:
    result: dict[str, EdgeDTO] = {}
    for declaration in declarations:
        metadata = _component_metadata(declaration)
        if metadata.kind != "edge":
            continue
        if metadata.source is None or metadata.target is None:
            raise ValueError(
                f"edge {metadata.name!r} does not declare both endpoints"
            )
        source = _component_metadata(metadata.source).name
        target = _component_metadata(metadata.target).name
        parent = (
            None if metadata.parent is None
            else _component_metadata(metadata.parent).name
        )
        labels, annotations = _labels_and_annotations("edge", metadata.annotations)
        result[metadata.name] = EdgeDTO(
            name=metadata.name,
            labels=labels,
            source=source,
            target=target,
            properties=tuple(_property_dto(item) for item in metadata.properties),
            annotations=annotations,
            abstract=metadata.abstract,
            parent=parent,
            description=metadata.description,
        )
    return result


def _nodes_of(
    declarations: Sequence[type[Any]],
) -> dict[str, NodeDTO]:
    result: dict[str, NodeDTO] = {}
    for declaration in declarations:
        metadata = _component_metadata(declaration)
        if metadata.kind != "node":
            continue
        parent = (
            None if metadata.parent is None
            else _component_metadata(metadata.parent).name
        )
        labels, annotations = _labels_and_annotations("node", metadata.annotations)
        result[metadata.name] = NodeDTO(
            name=metadata.name,
            labels=labels,
            properties=tuple(_property_dto(item) for item in metadata.properties),
            annotations=annotations,
            abstract=metadata.abstract,
            parent=parent,
            description=metadata.description,
        )
    return result


def _validate_acyclic(
    values: Sequence[NodeDTO] | Sequence[EdgeDTO],
) -> None:
    by_name: Mapping[str, NodeDTO | EdgeDTO] = {item.name: item for item in values}
    for item in values:
        seen: set[str] = set()
        current: str | None = item.name
        while current is not None:
            if current in seen:
                raise ValueError(
                    f"component parent chain cycle includes {current!r}"
                )
            seen.add(current)
            parent = by_name.get(current)
            current = None if parent is None else parent.parent


def collect_components(namespace: Namespace) -> Sequence[type[Any]]:
    """Select every graph-visible declaration reachable from the namespace."""
    return _component_closure(namespace.values())


def transcribe_graph_part(
    declarations: Sequence[object], context: Any = None,
) -> GraphPartDTO:
    """Turn collected declarations into the topology blueprint DTO."""
    del context
    classes: list[type[Any]] = []
    for declaration in declarations:
        if not isinstance(declaration, type):
            raise TypeError(
                f"topology declarations must be classes, not {declaration!r}"
            )
        classes.append(declaration)
    closure = _component_closure(tuple(classes))
    nodes = _nodes_of(closure)
    edges = _edges_of(closure)
    return GraphPartDTO(
        nodes=tuple(nodes[name] for name in sorted(nodes)),
        edges=tuple(edges[name] for name in sorted(edges)),
    )


def validate_graph_part(dto: GraphPartDTO) -> None:
    """Reject a topology DTO whose references or hierarchy are invalid."""
    if not isinstance(dto, GraphPartDTO):
        raise TypeError("topology requires a GraphPartDTO")
    nodes = {item.name: item for item in dto.nodes}
    edges = {item.name: item for item in dto.edges}
    for node in dto.nodes:
        if node.parent is None:
            continue
        parent = nodes.get(node.parent)
        if parent is None:
            raise ValueError(
                f"node {node.name!r} parent {node.parent!r} is not a node "
                "in this topology part"
            )
        if not parent.abstract:
            raise ValueError(
                f"node {node.name!r} parent {parent.name!r} is not abstract"
            )
    for edge in dto.edges:
        for side, name in (("source", edge.source), ("target", edge.target)):
            if name not in nodes:
                raise ValueError(
                    f"edge {edge.name!r} {side} {name!r} is not a node in "
                    "this topology part"
                )
        if edge.parent is None:
            continue
        parent = edges.get(edge.parent)
        if parent is None:
            raise ValueError(
                f"edge {edge.name!r} parent {edge.parent!r} is not an edge "
                "in this topology part"
            )
        if not parent.abstract:
            raise ValueError(
                f"edge {edge.name!r} parent {parent.name!r} is not abstract"
            )
    _validate_acyclic(dto.nodes)
    _validate_acyclic(dto.edges)


__all__ = [
    "collect_components", "transcribe_graph_part", "validate_graph_part",
]
