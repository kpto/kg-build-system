"""Canonical document codec for the annotation blueprint part."""
from __future__ import annotations

from collections.abc import Mapping

from pydantic import JsonValue

from .blueprint_dto import AnnotationDTO


def _text(value: Mapping[str, JsonValue], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"annotation field {key!r} must be a non-empty string")
    return result


def annotation_to_document(dto: AnnotationDTO) -> dict[str, JsonValue]:
    """Encode one annotation DTO as its canonical JSON-compatible document.

    Example:
        ```python
        from kg_build_system.declaration.foundations.annotations.internal import (
            AnnotationDTO, annotation_to_document,
        )

        document = annotation_to_document(
            AnnotationDTO("example", "owner", {"name": "Ada"})
        )
        ```
    """
    return {
        "namespace": dto.namespace,
        "id": dto.id,
        "arguments": dto.arguments,
    }


def annotation_from_document(document: Mapping[str, JsonValue]) -> AnnotationDTO:
    """Decode one annotation DTO from its canonical document.

    Example:
        ```python
        from kg_build_system.declaration.foundations.annotations.internal import (
            annotation_from_document,
        )

        dto = annotation_from_document({
            "namespace": "example", "id": "owner", "arguments": {"name": "Ada"},
        })
        ```
    """
    if not isinstance(document, Mapping):
        raise ValueError("an annotation document must be an object")
    return AnnotationDTO(
        namespace=_text(document, "namespace"),
        id=_text(document, "id"),
        arguments=document.get("arguments"),
    )


__all__ = ["annotation_from_document", "annotation_to_document"]
