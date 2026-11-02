"""Internal annotation interface."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from typing import Any

from .labels import EdgeLabel, NodeLabel
from .models import Annotation, annotation_tuple as _annotation_tuple


def _annotation_payload(annotation: Annotation) -> tuple[str, str, dict[str, Any]]:
    return annotation.namespace, annotation.annotation_id, asdict(annotation)


def _annotation_irs(annotations: Sequence[Annotation]) -> tuple[Any, ...]:
    from .ir import AnnotationIR

    return tuple(
        AnnotationIR(namespace, annotation_id, arguments)
        for namespace, annotation_id, arguments in (
            _annotation_payload(value) for value in annotations
        )
    )


def annotation_payload(annotation: Annotation) -> tuple[str, str, dict[str, Any]]:
    """Return one annotation as its namespace, id and field payload.

    Example:
        ```python
        from kg_build_system.annotations import NodeLabel
        from kg_build_system.annotations.interfaces import annotation_payload

        annotation_payload(NodeLabel("Sensor"))
        ```
    """
    return _annotation_payload(annotation)


def annotation_irs(annotations: Sequence[Annotation]) -> tuple[Any, ...]:
    """Lower annotations to their frozen compilation IR values.

    Example:
        ```python
        from kg_build_system.annotations import NodeLabel
        from kg_build_system.annotations.interfaces import annotation_irs

        annotation_irs([NodeLabel("Sensor")])
        ```
    """
    return _annotation_irs(annotations)


def annotation_tuple(values: Sequence[Annotation]) -> tuple[Annotation, ...]:
    """Return the values as a tuple, rejecting anything that is not an annotation.

    Example:
        ```python
        from kg_build_system.annotations import NodeLabel
        from kg_build_system.annotations.interfaces import annotation_tuple

        annotation_tuple([NodeLabel("Sensor")])
        ```
    """
    return _annotation_tuple(values)


__all__ = [
    "Annotation", "EdgeLabel", "NodeLabel", "annotation_irs", "annotation_payload",
    "annotation_tuple",
]
