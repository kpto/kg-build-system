"""Canonical JSON codec for the graph declaration DTO."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kg_build_system.distribution.languages.semantics.service.internal import (
    semantics_from_document,
    semantics_to_document,
)

from ...model.internal.dto.graph_dto import GraphDeclarationDTO


def _object(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be an object")
    return value


def _text(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"{key!r} must be a non-empty string")
    return result


def _optional_text(value: Mapping[str, Any], key: str) -> str | None:
    result = value.get(key)
    if result is not None and (not isinstance(result, str) or not result):
        raise ValueError(f"{key!r} must be null or a non-empty string")
    return result


def graph_declaration_to_document(
    value: GraphDeclarationDTO,
) -> dict[str, Any]:
    """Encode the graph declaration as a JSON-compatible object."""
    document: dict[str, Any] = {"name": value.name}
    if value.description is not None:
        document["description"] = value.description
    document["semantics"] = semantics_to_document(value.semantics)
    return document


def graph_declaration_from_document(value: Any) -> GraphDeclarationDTO:
    """Rebuild the graph declaration from its JSON-compatible object."""
    document = _object(value, "a graph declaration")
    if "semantics" not in document:
        raise ValueError("a graph declaration requires semantics")
    semantics = semantics_from_document(document["semantics"])
    if semantics.purpose is None:
        raise ValueError(
            "a graph declaration semantics document requires a purpose"
        )
    return GraphDeclarationDTO(
        name=_text(document, "name"),
        description=_optional_text(document, "description"),
        semantics=semantics,
    )


__all__ = [
    "graph_declaration_from_document", "graph_declaration_to_document",
]
