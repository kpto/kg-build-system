"""Immutable graph binding models."""
from dataclasses import dataclass
from typing import Any

from ..expressions import Expression, FieldPath

@dataclass(frozen=True)
class NodeBinding:
    target: type
    build_key: Expression[Any] | FieldPath[Any]
    properties: Any

@dataclass(frozen=True)
class EdgeBinding:
    target: type
    build_key: Expression[Any] | FieldPath[Any]
    source_build_key: Expression[Any] | FieldPath[Any]
    target_build_key: Expression[Any] | FieldPath[Any]
    properties: Any
