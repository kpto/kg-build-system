"""Canonical JSON codec for the topology blueprint DTO."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from kg_build_system.declaration.foundations.annotations.internal import (
    annotation_from_document,
    annotation_to_document,
)
from kg_build_system.kernel.internal.types import type_from_document, type_to_document

from ..internal.dto.blueprint_dto import (
    EdgeDTO, GraphPartDTO, NodeDTO, PropertyDTO,
)


def _object(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be an object")
    return value


def _array(value: Any, context: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{context} must be an array")
    return value


def _text(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"{key!r} must be a non-empty string")
    return result


def _optional_text(value: Mapping[str, Any], key: str) -> str | None:
    result = value.get(key)
    if result is None:
        return None
    if not isinstance(result, str) or not result:
        raise ValueError(f"{key!r} must be null or a non-empty string")
    return result


def _labels(value: Mapping[str, Any]) -> tuple[str, ...]:
    result = tuple(_array(value.get("labels", ()), "labels"))
    if any(not isinstance(item, str) or not item for item in result):
        raise ValueError("'labels' must contain non-empty strings")
    return result


def _property_to_document(value: PropertyDTO) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": value.name,
        "logical_type": type_to_document(value.logical_type),
        "annotations": [annotation_to_document(item) for item in value.annotations],
    }
    if value.description is not None:
        result["description"] = value.description
    return result


def _property_from_document(value: Mapping[str, Any]) -> PropertyDTO:
    return PropertyDTO(
        name=_text(value, "name"),
        logical_type=type_from_document(_object(value.get("logical_type"), "logical_type")),
        description=_optional_text(value, "description"),
        annotations=tuple(
            annotation_from_document(_object(item, "property annotation"))
            for item in _array(value.get("annotations", ()), "annotations")
        ),
    )


def _common_to_document(value: NodeDTO | EdgeDTO) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": value.name,
        "labels": list(value.labels),
        "abstract": value.abstract,
        "properties": [_property_to_document(item) for item in value.properties],
        "annotations": [annotation_to_document(item) for item in value.annotations],
    }
    if value.parent is not None:
        result["parent"] = value.parent
    if value.description is not None:
        result["description"] = value.description
    return result


def _node_to_document(value: NodeDTO) -> dict[str, Any]:
    return _common_to_document(value)


def _edge_to_document(value: EdgeDTO) -> dict[str, Any]:
    result = _common_to_document(value)
    result["source"] = value.source
    result["target"] = value.target
    return result


def _common_from_document(value: Mapping[str, Any]) -> dict[str, Any]:
    abstract = value.get("abstract", False)
    if not isinstance(abstract, bool):
        raise ValueError("'abstract' must be a boolean")
    return {
        "name": _text(value, "name"),
        "labels": _labels(value),
        "properties": tuple(
            _property_from_document(_object(item, "property"))
            for item in _array(value.get("properties", ()), "properties")
        ),
        "annotations": tuple(
            annotation_from_document(_object(item, "annotation"))
            for item in _array(value.get("annotations", ()), "annotations")
        ),
        "abstract": abstract,
        "parent": _optional_text(value, "parent"),
        "description": _optional_text(value, "description"),
    }


def _node_from_document(value: Mapping[str, Any]) -> NodeDTO:
    return NodeDTO(**_common_from_document(value))


def _edge_from_document(value: Mapping[str, Any]) -> EdgeDTO:
    common = _common_from_document(value)
    return EdgeDTO(
        **common,
        source=_text(value, "source"),
        target=_text(value, "target"),
    )


def graph_to_document(part: GraphPartDTO) -> dict[str, Any]:
    """Encode the topology part as a JSON-compatible object.

    Example:
        ```python
        from kg_build_system.declaration.languages.topology.internal.dto import (
            GraphPartDTO, graph_to_document,
        )

        document = graph_to_document(GraphPartDTO())
        assert document == {"nodes": [], "edges": []}
        ```
    """
    return {
        "nodes": [_node_to_document(item) for item in part.nodes],
        "edges": [_edge_to_document(item) for item in part.edges],
    }


def graph_from_document(document: Mapping[str, Any]) -> GraphPartDTO:
    """Rebuild the topology part from its JSON-compatible object.

    Example:
        ```python
        from kg_build_system.declaration.languages.topology.internal.dto import (
            graph_from_document,
        )

        part = graph_from_document({"nodes": [], "edges": []})
        ```
    """
    return GraphPartDTO(
        nodes=tuple(
            _node_from_document(_object(item, "node"))
            for item in _array(document.get("nodes", ()), "nodes")
        ),
        edges=tuple(
            _edge_from_document(_object(item, "edge"))
            for item in _array(document.get("edges", ()), "edges")
        ),
    )


__all__ = ["graph_from_document", "graph_to_document"]
