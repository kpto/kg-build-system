"""Compilation IR for annotations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AnnotationIR:
    namespace: str
    annotation_id: str
    arguments: Any


__all__ = ["AnnotationIR"]
