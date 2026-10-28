"""Authoring row sources produced by shape-preserving filters."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from ..expressions import BoolExpression
from ..types import Shape
from .models import RowSource


S = TypeVar("S", bound=Shape)


@dataclass(frozen=True, slots=True)
class DerivedRowSource(RowSource[S], Generic[S]):
    """A filtered row source that preserves the shape of its source."""

    shape: type[S]
    source: type[S]
    filters: tuple[BoolExpression, ...] = ()

    def where(self, predicate: Callable[[type[S]], BoolExpression]) -> "DerivedRowSource[S]":
        if not callable(predicate):
            raise TypeError("where requires a callable predicate")
        result = predicate(self.shape)
        if not isinstance(result, BoolExpression):
            raise TypeError("where predicates must return a BoolExpression")
        return DerivedRowSource(self.shape, self.source, (*self.filters, result))

    def projection_base(self) -> type:
        from .models import projection_base

        return projection_base(self)


__all__ = ["DerivedRowSource"]
