"""Framework-internal interface of the annotation foundation.

Other subpackages use this surface to validate annotation sequences, read an
annotation as a ``(namespace, id, arguments)`` payload and convert it to the
blueprint DTO. The author-facing names are :mod:`...annotations.public`.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .._private.payload import annotation_dtos as _annotation_dtos
from .._private.payload import annotation_payload as _annotation_payload
from .._private.validation import annotation_tuple as _annotation_tuple
from ..public.model.base import Annotation
from ..public.model.labels import EdgeLabel, NodeLabel
from .dto.blueprint_dto import AnnotationDTO
from .dto.codec import annotation_from_document, annotation_to_document
from .service.source import render_annotation_source


def annotation_payload(annotation: Annotation) -> tuple[str, str, dict[str, Any]]:
    """Return one annotation as its namespace, id and field payload.

    Example:
        ```python
        from kg_build_system.declaration.foundations.annotations import NodeLabel
        from kg_build_system.declaration.foundations.annotations.internal import (
            annotation_payload,
        )

        annotation_payload(NodeLabel("Sensor"))
        ```
    """
    return _annotation_payload(annotation)


def annotation_dtos(annotations: Sequence[Annotation]) -> tuple[AnnotationDTO, ...]:
    """Return annotations as their portable blueprint DTOs.

    Example:
        ```python
        from kg_build_system.declaration.foundations.annotations import NodeLabel
        from kg_build_system.declaration.foundations.annotations.internal import (
            annotation_dtos,
        )

        annotation_dtos([NodeLabel("Sensor")])
        ```
    """
    return _annotation_dtos(annotations)


def annotation_tuple(values: Sequence[Annotation]) -> tuple[Annotation, ...]:
    """Return the values as a tuple, rejecting anything that is not an annotation.

    Example:
        ```python
        from kg_build_system.declaration.foundations.annotations import NodeLabel
        from kg_build_system.declaration.foundations.annotations.internal import (
            annotation_tuple,
        )

        annotation_tuple([NodeLabel("Sensor")])
        ```
    """
    return _annotation_tuple(values)


__all__ = [
    "Annotation", "AnnotationDTO", "EdgeLabel", "NodeLabel", "annotation_dtos",
    "annotation_from_document", "annotation_payload", "annotation_to_document",
    "annotation_tuple", "render_annotation_source",
]
