"""Immutable graph binding models."""
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from ..annotations import Annotation, annotation_tuple
from ..expressions import Expression
from ..topology.models import Edge, GraphValue, Node, PropertySlot

T = TypeVar("T", bound=GraphValue)
N_co = TypeVar("N_co", bound=Node, covariant=True)
E_co = TypeVar("E_co", bound=Edge[Any, Any], covariant=True)

@dataclass(frozen=True, kw_only=True)
class ExpressionBinding(PropertySlot[T], Generic[T]):
    """An explicitly bound portable expression."""

    expression: Expression[T]


@dataclass(frozen=True)
class BindingOptions:
    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None: object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))

@dataclass(frozen=True)
class NodeBinding(Generic[N_co]):
    debug_name: str | None
    target: type[N_co]
    build_key: ExpressionBinding[str]
    properties: N_co
    annotations: tuple[Annotation, ...] = ()

@dataclass(frozen=True)
class EdgeBinding(Generic[E_co]):
    debug_name: str | None
    target: type[E_co]
    build_key: ExpressionBinding[str]
    source_build_key: ExpressionBinding[str]
    target_build_key: ExpressionBinding[str]
    properties: E_co
    annotations: tuple[Annotation, ...] = ()


type Binding = NodeBinding[Any] | EdgeBinding[Any]
