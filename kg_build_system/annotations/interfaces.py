"""Framework-internal interface of the annotation domain."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from typing import Any

from .labels import EdgeLabel, NodeLabel
from .models import Annotation, annotation_tuple

__all__ = [
    "Annotation",
    "EdgeLabel",
    "Label",
    "NodeLabel",
    "annotation_payload",
    "annotation_tuple",
]

Label = NodeLabel | EdgeLabel


def annotation_payload(annotation: Annotation) -> tuple[str, str, dict[str, Any]]:
    """The ``(namespace, id, arguments)`` form an annotation takes in the IR."""
    return annotation.namespace, annotation.annotation_id, asdict(annotation)


def annotations_payload(
    annotations: Sequence[Annotation],
) -> tuple[tuple[str, str, dict[str, Any]], ...]:
    """The IR form of an annotation sequence."""
    return tuple(annotation_payload(value) for value in annotations)
