"""Portable annotations."""
from __future__ import annotations

from .interfaces import (
    annotation_irs, annotation_payload, annotation_tuple,
)
from .labels import EdgeLabel, NodeLabel
from .models import Annotation

__all__ = [
    "Annotation", "EdgeLabel", "NodeLabel", "annotation_irs",
    "annotation_payload", "annotation_tuple",
]
