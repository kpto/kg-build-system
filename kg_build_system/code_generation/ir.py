"""Generated-declaration IR.

The provider output tree is frozen data: it states what to render, not how to
render it. Rendering is an engine concern.
"""
from __future__ import annotations

from .models import (
    GeneratedAnnotation,
    GeneratedArrayType,
    GeneratedClass,
    GeneratedField,
    GeneratedFile,
    GeneratedMember,
    GeneratedNullableType,
    GeneratedPackage,
    GeneratedScalarType,
    GeneratedStructType,
    GeneratedType,
    NullabilityNote,
)

__all__ = [
    "GeneratedAnnotation",
    "GeneratedArrayType",
    "GeneratedClass",
    "GeneratedField",
    "GeneratedFile",
    "GeneratedMember",
    "GeneratedNullableType",
    "GeneratedPackage",
    "GeneratedScalarType",
    "GeneratedStructType",
    "GeneratedType",
    "NullabilityNote",
]
