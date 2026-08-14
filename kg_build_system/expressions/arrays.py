"""Typed array expressions and explicit row expansion."""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Generic, TypeVar, cast

from ..types import Array, ArrayType, NullableType
from .base import operation
from .codec import encode_expression
from .ir import FieldReferenceExpression, RowSemantics
from .nullable import NullableValueExpression
from .values import ValueExpression


TItem = TypeVar("TItem")
TItemExpr = TypeVar("TItemExpr", bound=ValueExpression)
TItemNullExpr = TypeVar("TItemNullExpr", bound=ValueExpression)


def _expansion_scope(expression) -> tuple[str, ...]:
    if isinstance(expression, FieldReferenceExpression):
        return (expression.source, *expression.path)
    encoded = json.dumps(
        encode_expression(expression), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return ("expression", sha256(encoded).hexdigest())


class ArrayValueExpression(
    ValueExpression[Array[TItem]], Generic[TItem, TItemExpr]
):
    def __init__(self, expression) -> None:
        if not isinstance(expression.logical_type, ArrayType):
            raise TypeError("ArrayValueExpression requires an array logical type")
        super().__init__(expression)

    def each(self) -> TItemExpr:
        from .factory import wrap_expression

        logical_type = self.logical_type
        assert isinstance(logical_type, ArrayType)
        result = operation(
            "each",
            self.expression,
            logical_type=logical_type.item,
            row_semantics=RowSemantics("expand", _expansion_scope(self.expression)),
        )
        return cast(TItemExpr, wrap_expression(result))


class ArrayNullableValueExpression(
    NullableValueExpression[Array[TItem], ArrayValueExpression[TItem, TItemExpr]],
    Generic[TItem, TItemExpr, TItemNullExpr],
):
    """A nullable array; expansion suppresses a null array automatically."""

    def __init__(self, expression) -> None:
        logical_type = expression.logical_type
        if not (
            isinstance(logical_type, NullableType)
            and isinstance(logical_type.value, ArrayType)
        ):
            raise TypeError("ArrayNullableValueExpression requires a nullable array type")
        super().__init__(expression, ArrayValueExpression)

    def each(self) -> TItemExpr:
        from .factory import wrap_expression

        logical_type = self.logical_type
        assert isinstance(logical_type, NullableType)
        assert isinstance(logical_type.value, ArrayType)
        result = operation(
            "each",
            self.expression,
            logical_type=logical_type.value.item,
            row_semantics=RowSemantics("expand", _expansion_scope(self.expression)),
        )
        return cast(TItemExpr, wrap_expression(result))


__all__ = ["ArrayNullableValueExpression", "ArrayValueExpression"]
