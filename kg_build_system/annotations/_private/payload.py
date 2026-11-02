"""Lower annotations to their payload and compilation IR forms."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from typing import Any

from ..public.models import Annotation


def annotation_payload(annotation: Annotation) -> tuple[str, str, dict[str, Any]]:
    """Return one annotation as its namespace, id and field payload."""
    return annotation.namespace, annotation.annotation_id, asdict(annotation)


def annotation_irs(annotations: Sequence[Annotation]) -> tuple[Any, ...]:
    """Lower annotations to their frozen compilation IR values."""
    from ..internal.ir import AnnotationIR

    return tuple(
        AnnotationIR(namespace, annotation_id, arguments)
        for namespace, annotation_id, arguments in (
            annotation_payload(value) for value in annotations
        )
    )


__all__ = ["annotation_irs", "annotation_payload"]
