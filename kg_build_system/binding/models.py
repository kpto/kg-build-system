"""Immutable graph binding models."""
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from ..annotations import Annotation, annotation_tuple
from ..expressions import Expression
from ..topology.models import PropertySlot

T = TypeVar("T")

@dataclass(frozen=True)
class ExpressionBinding(PropertySlot[T], Generic[T]):
    expression: Expression[T] | None = None


@dataclass(frozen=True)
class BindingOptions:
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None: object.__setattr__(self, "annotations", annotation_tuple(self.annotations))

@dataclass(frozen=True)
class NodeBinding:
    debug_name: str | None
    target: type
    build_key: Expression[Any]
    properties: Any
    annotations: tuple[Annotation, ...] = ()

@dataclass(frozen=True)
class EdgeBinding:
    debug_name: str | None
    target: type
    build_key: Expression[Any]
    source_build_key: Expression[Any]
    target_build_key: Expression[Any]
    properties: Any
    annotations: tuple[Annotation, ...] = ()
