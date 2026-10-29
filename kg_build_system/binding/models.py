"""Immutable graph-binding authoring models."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from ..annotations.interfaces import Annotation, annotation_tuple
from ..expressions.interfaces import ValueExpression
from ..table.interfaces import DerivedRowSource
from ..topology.interfaces import Edge, Node

N_co = TypeVar("N_co", bound=Node, covariant=True)
E_co = TypeVar("E_co", bound=Edge[Any, Any], covariant=True)
K = TypeVar("K")
SK = TypeVar("SK")
TK = TypeVar("TK")


@dataclass(frozen=True)
class BindingOptions:
    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


@dataclass(frozen=True)
class NodeValues(Generic[N_co, K]):
    """The row-derived values one node binding supplies."""

    build_key: Any
    properties: N_co


@dataclass(frozen=True)
class EdgeValues(Generic[E_co, K, SK, TK]):
    """The row-derived values one edge binding supplies."""

    build_key: Any
    source_build_key: Any
    target_build_key: Any
    properties: E_co


@dataclass(frozen=True)
class NodeBinding(Generic[N_co]):
    debug_name: str | None
    target: type[N_co]
    build_key: ValueExpression[Any]
    properties: N_co
    annotations: tuple[Annotation, ...] = ()
    rows: Any = None


@dataclass(frozen=True)
class EdgeBinding(Generic[E_co]):
    debug_name: str | None
    target: type[E_co]
    build_key: ValueExpression[Any]
    source_build_key: ValueExpression[Any]
    target_build_key: ValueExpression[Any]
    properties: E_co
    annotations: tuple[Annotation, ...] = ()
    source_node: type[Node] | None = None
    target_node: type[Node] | None = None
    rows: Any = None


type Binding = NodeBinding[Any] | EdgeBinding[Any]

__all__ = ["Binding", "BindingOptions", "EdgeBinding", "NodeBinding"]
