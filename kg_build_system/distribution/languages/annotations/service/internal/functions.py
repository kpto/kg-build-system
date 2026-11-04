"""Annotation payload, DTO and validation helpers."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ...model.internal.dto.blueprint_dto import AnnotationDTO
from ...model.public.base import Annotation


def annotation_payload(annotation: Annotation) -> tuple[str, str, dict[str, Any]]:
    """Return one annotation as its namespace, id and field payload."""
    from .._private.payload import annotation_payload as payload

    return payload(annotation)


def annotation_dtos(annotations: Sequence[Annotation]) -> tuple[AnnotationDTO, ...]:
    """Return annotations as their portable blueprint DTOs."""
    from .._private.payload import annotation_dtos as build

    return build(annotations)


def annotation_tuple(values: Sequence[Annotation]) -> tuple[Annotation, ...]:
    """Return the values as a tuple, rejecting anything that is not an annotation."""
    from .._private.validation import annotation_tuple as validate

    return validate(values)


__all__ = ["annotation_dtos", "annotation_payload", "annotation_tuple"]
