"""Read annotations as their portable payload and blueprint DTO forms."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from typing import TYPE_CHECKING, Any, cast

from ...model.public.base import Annotation

if TYPE_CHECKING:
    from pydantic import JsonValue

    from ...model.internal.dto.blueprint_dto import AnnotationDTO


def annotation_payload(annotation: Annotation) -> tuple[str, str, dict[str, Any]]:
    """Return one annotation as its namespace, id and field payload."""
    return annotation.namespace, annotation.annotation_id, asdict(annotation)


def annotation_dtos(annotations: Sequence[Annotation]) -> tuple[AnnotationDTO, ...]:
    """Return annotations as their portable blueprint DTOs."""
    from ...model.internal.dto.blueprint_dto import AnnotationDTO

    return tuple(
        AnnotationDTO(namespace, annotation_id, cast("JsonValue", arguments))
        for namespace, annotation_id, arguments in (
            annotation_payload(value) for value in annotations
        )
    )


__all__ = ["annotation_dtos", "annotation_payload"]
