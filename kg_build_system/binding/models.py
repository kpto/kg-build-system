"""Immutable graph-binding authoring models."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from ..annotations import Annotation, annotation_tuple
from ..expressions import ValueExpression
from ..topology.models import Edge, Node

N_co = TypeVar("N_co", bound=Node, covariant=True)
E_co = TypeVar("E_co", bound=Edge[Any, Any], covariant=True)


@dataclass(frozen=True)
class BindingOptions:
    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


@dataclass(frozen=True)
class NodeBinding(Generic[N_co]):
    debug_name: str | None
    target: type[N_co]
    build_key: ValueExpression[Any]
    properties: N_co
    annotations: tuple[Annotation, ...] = ()


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


type Binding = NodeBinding[Any] | EdgeBinding[Any]

__all__ = ["Binding", "BindingOptions", "EdgeBinding", "NodeBinding"]
