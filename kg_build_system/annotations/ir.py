"""Compilation IR for annotations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AnnotationIR:
    """A portable annotation in the compilation IR.

    Example:
        ```python
        from kg_build_system.annotations.ir import AnnotationIR

        AnnotationIR(
            "kg_build_system.topology", "node_label", {"label": "Sensor"},
        )
        ```
    """

    namespace: str
    annotation_id: str
    arguments: Any


__all__ = ["AnnotationIR"]
