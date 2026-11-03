"""Canonical document codec for the annotation blueprint part."""
from __future__ import annotations

from collections.abc import Mapping

from pydantic import JsonValue

from ...model.internal.dto.blueprint_dto import AnnotationDTO


def text(value: Mapping[str, JsonValue], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"annotation field {key!r} must be a non-empty string")
    return result


def annotation_to_document(dto: AnnotationDTO) -> dict[str, JsonValue]:
    """Encode one annotation DTO as its canonical JSON-compatible document."""
    return {
        "namespace": dto.namespace,
        "id": dto.id,
        "arguments": dto.arguments,
    }


def annotation_from_document(document: Mapping[str, JsonValue]) -> AnnotationDTO:
    """Decode one annotation DTO from its canonical document."""
    if not isinstance(document, Mapping):
        raise ValueError("an annotation document must be an object")
    return AnnotationDTO(
        namespace=text(document, "namespace"),
        id=text(document, "id"),
        arguments=document.get("arguments"),
    )


__all__ = ["annotation_from_document", "annotation_to_document"]
