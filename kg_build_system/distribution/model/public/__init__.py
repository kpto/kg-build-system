"""The distribution's authoring model: build settings and typed references."""
from __future__ import annotations

from .refs import (
    EdgeRef, FieldRef, NodeRef, OperationRef, PropertyRef, Ref, RelationRef,
    SourceRef, ref_from_document, ref_to_document,
)
from .runtime import BuildRuntime

__all__ = [
    "BuildRuntime", "EdgeRef", "FieldRef", "NodeRef", "OperationRef",
    "PropertyRef", "Ref", "RelationRef", "SourceRef", "ref_from_document",
    "ref_to_document",
]
