"""Compiler-facing typed expression wrapper.

This module is internal machinery behind :class:`Selection`; it is not part of
the authoring facade. A ``ValueExpression`` holds one immutable expression node
and exposes only the operations the compiler needs.
"""
from __future__ import annotations

from typing import Any

from kg_build_system.kernel.model.public.types import LogicalType, NullableType, UnitType
from ...model.internal.model import ExpressionNode


class ValueExpression[T]:
    """One immutable compiler expression node."""

    __slots__ = ("_model",)

    def __init__(self, model: ExpressionNode) -> None:
        self._model = model

    @property
    def model(self) -> ExpressionNode:
        """The canonical expression node behind this wrapper."""
        return self._model

    @property
    def logical_type(self) -> LogicalType:
        """The canonical logical type of the expression."""
        return self._model.logical_type

    def to_string(self) -> "ValueExpression[Any]":
        """Render this scalar as canonical text for keys and identifiers."""
        logical_type = self.logical_type
        base = (
            logical_type.value
            if isinstance(logical_type, NullableType)
            else logical_type
        )
        if not isinstance(base, UnitType):
            raise TypeError(
                f"to_string() requires a scalar unit, not {logical_type!r}"
            )
        from ...service._private.apply import apply_operation

        return ValueExpression(apply_operation("to_string", self._model).model)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._model!r})"


__all__ = ["ValueExpression"]
