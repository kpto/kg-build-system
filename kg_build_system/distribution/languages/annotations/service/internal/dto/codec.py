"""Canonical document codec for the annotation blueprint part."""
from __future__ import annotations

from collections.abc import Mapping

from pydantic import JsonValue

from ....model.internal.dto.blueprint_dto import AnnotationDTO


def annotation_to_document(dto: AnnotationDTO) -> dict[str, JsonValue]:
    """Encode one annotation DTO as its canonical JSON-compatible document.

    Example:
        ```python
        from kg_build_system.distribution.languages.annotations.service.internal import (
            AnnotationDTO, annotation_to_document,
        )

        document = annotation_to_document(
            AnnotationDTO("example", "owner", {"name": "Ada"})
        )
        ```
    """
    from ..._private.codec import annotation_to_document as encode

    return encode(dto)


def annotation_from_document(document: Mapping[str, JsonValue]) -> AnnotationDTO:
    """Decode one annotation DTO from its canonical document.

    Example:
        ```python
        from kg_build_system.distribution.languages.annotations.service.internal import (
            annotation_from_document,
        )

        dto = annotation_from_document({
            "namespace": "example", "id": "owner", "arguments": {"name": "Ada"},
        })
        ```
    """
    from ..._private.codec import annotation_from_document as decode

    return decode(document)


__all__ = ["annotation_from_document", "annotation_to_document"]
