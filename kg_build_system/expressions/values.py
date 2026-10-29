"""Bindable typed calculations backed by expression domain models."""
from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar, cast, overload

from ..types.interfaces import (
    Date, LogicalType, Nullable, NullableType, STR, Time, Timestamp,
    UnitType, Uuid,
)
from .models import ExpressionNode

if TYPE_CHECKING:
    from .nullable import NullableExpression
    from .text import StrExpression


T_co = TypeVar("T_co", covariant=True)
type TextualScalar = bool | int | float | str | Date | Time | Timestamp | Uuid
TText = TypeVar("TText", bound=TextualScalar)


class NullableAuthoringInput(Generic[T_co]):
    """Typing bridge from internal ``Nullable[T]`` to author-facing ``T | None``."""


class ValueExpression(Generic[T_co]):
    """Bindable calculation backed by one immutable expression model.

    This base deliberately exposes no value-specific operations. Concrete
    expression families add only the operations valid for their logical type.
    """

    __slots__ = ("_model",)

    def __init__(self, model: ExpressionNode) -> None:
        self._model = model

    @property
    def model(self) -> ExpressionNode:
        return self._model

    @property
    def logical_type(self) -> LogicalType:
        return self._model.logical_type

    @overload
    def to_string(
        self: "ValueExpression[Nullable[TText]]",
    ) -> "NullableExpression[str, StrExpression]": ...
    @overload
    def to_string(self: "ValueExpression[TText]") -> "StrExpression": ...
    def to_string(self) -> "StrExpression | NullableExpression[str, StrExpression]":
        """Render this scalar as canonical text for keys and identifiers.

        Bool, int, float, str, date, time, timestamp and uuid are accepted.
        Timestamps carry the `T` separator the framework's canonical text uses;
        every other unit uses DuckDB's canonical cast. Arrays and structs have
        no single text form and are refused.
        """
        logical_type = self.logical_type
        base = (
            logical_type.value
            if isinstance(logical_type, NullableType) else logical_type
        )
        if not isinstance(base, UnitType):
            raise TypeError(
                f"to_string() requires a scalar unit, not {logical_type!r}"
            )
        from .base import operation
        from .factory import wrap_expression

        result_type = NullableType(STR) if isinstance(logical_type, NullableType) else STR
        return cast(
            "StrExpression | NullableExpression[str, StrExpression]",
            wrap_expression(operation("to_string", self._model, logical_type=result_type)),
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._model!r})"


__all__ = ["NullableAuthoringInput", "ValueExpression"]
