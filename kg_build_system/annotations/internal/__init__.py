"""Internal annotation interface."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .._private.payload import (
    annotation_irs as _annotation_irs,
    annotation_payload as _annotation_payload,
)
from .._private.validation import annotation_tuple as _annotation_tuple
from ..public.labels import EdgeLabel, NodeLabel
from ..public.models import Annotation


def annotation_payload(annotation: Annotation) -> tuple[str, str, dict[str, Any]]:
    """Return one annotation as its namespace, id and field payload.

    Example:
        ```python
        from kg_build_system.annotations import NodeLabel
        from kg_build_system.annotations.internal import annotation_payload

        annotation_payload(NodeLabel("Sensor"))
        ```
    """
    return _annotation_payload(annotation)


def annotation_irs(annotations: Sequence[Annotation]) -> tuple[Any, ...]:
    """Lower annotations to their frozen compilation IR values.

    Example:
        ```python
        from kg_build_system.annotations import NodeLabel
        from kg_build_system.annotations.internal import annotation_irs

        annotation_irs([NodeLabel("Sensor")])
        ```
    """
    return _annotation_irs(annotations)


def annotation_tuple(values: Sequence[Annotation]) -> tuple[Annotation, ...]:
    """Return the values as a tuple, rejecting anything that is not an annotation.

    Example:
        ```python
        from kg_build_system.annotations import NodeLabel
        from kg_build_system.annotations.internal import annotation_tuple

        annotation_tuple([NodeLabel("Sensor")])
        ```
    """
    return _annotation_tuple(values)


__all__ = [
    "Annotation", "EdgeLabel", "NodeLabel", "annotation_irs", "annotation_payload",
    "annotation_tuple",
]
