"""Internal annotation interface."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from typing import Any

from .labels import EdgeLabel, NodeLabel
from .models import Annotation, annotation_tuple


def annotation_payload(annotation: Annotation) -> tuple[str, str, dict[str, Any]]:
    return annotation.namespace, annotation.annotation_id, asdict(annotation)


def annotation_irs(annotations: Sequence[Annotation]) -> tuple[Any, ...]:
    from .ir import AnnotationIR

    return tuple(
        AnnotationIR(namespace, annotation_id, arguments)
        for namespace, annotation_id, arguments in (
            annotation_payload(value) for value in annotations
        )
    )


__all__ = [
    "Annotation", "EdgeLabel", "NodeLabel", "annotation_irs", "annotation_payload",
    "annotation_tuple",
]
