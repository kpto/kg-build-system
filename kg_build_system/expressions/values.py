"""Typed authoring wrappers around the canonical expression IR."""
from __future__ import annotations

from typing import Generic, TypeVar

from ..types import LogicalType
from .models import ExpressionNode


T_co = TypeVar("T_co", covariant=True)
T_authoring_co = TypeVar("T_authoring_co", covariant=True)


class AuthoringValueExpression(Generic[T_authoring_co]):
    """Static marker for the Python authoring type produced by an expression.

    Canonical expression types use ``Nullable[T]`` internally, while graph
    declarations use the author-facing ``T | None`` spelling.  This separate
    covariant marker lets an expression expose both views without weakening
    either one to ``Any``.
    """


class ValueExpression(Generic[T_co]):
    """Bindable typed value backed by one canonical expression node.

    This base deliberately exposes no value-specific operations. Concrete
    expression families add only the operations valid for their logical type.
    """

    __slots__ = ("_expression",)

    def __init__(self, expression: ExpressionNode) -> None:
        self._expression = expression

    @property
    def expression(self) -> ExpressionNode:
        return self._expression

    @property
    def logical_type(self) -> LogicalType:
        return self._expression.logical_type

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._expression!r})"


__all__ = ["AuthoringValueExpression", "ValueExpression"]
