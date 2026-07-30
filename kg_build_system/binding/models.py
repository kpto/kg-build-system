"""Immutable graph binding models."""
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from ..expressions import Expression
from ..topology.models import PropertySlot

T = TypeVar("T")

@dataclass(frozen=True)
class ExpressionBinding(PropertySlot[T], Generic[T]):
    expression: Expression[T] | None = None

@dataclass(frozen=True)
class NodeBinding:
    target: type
    build_key: Expression[Any]
    properties: Any

@dataclass(frozen=True)
class EdgeBinding:
    target: type
    build_key: Expression[Any]
    source_build_key: Expression[Any]
    target_build_key: Expression[Any]
    properties: Any
