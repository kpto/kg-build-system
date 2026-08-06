"""Scalar portable expression constructors."""
from typing import Any, Literal, overload

from ..data_types import validate_value_type
from .core import Expression, ValueRef, item_type
from .inputs import ExpressionInput, to_expression


class ValueExpressions:
    @overload
    def literal[T](self, value: ValueRef[T] | Expression[T]) -> Expression[T]: ...

    @overload
    def literal[T](self, value: T) -> Expression[T]: ...

    def literal(self, value: Any) -> Expression[Any]:
        return to_expression(value)

    def concat(self, *values: ExpressionInput[str]) -> Expression[str]:
        return Expression("concat", tuple(to_expression(value) for value in values), str)

    def coalesce[T](self, *values: ExpressionInput[T]) -> Expression[T]:
        expressions = tuple(to_expression(value) for value in values)
        if not expressions:
            raise ValueError("coalesce requires at least one value")
        return Expression("coalesce", expressions, expressions[0].type_hint)

    @overload
    def cast(self, value: ValueRef[list[str]] | Expression[list[str]], sql_type: Literal["VARCHAR[]", "TEXT[]"]) -> Expression[list[str]]: ...

    @overload
    def cast(self, value: Any, sql_type: str) -> Expression[Any]: ...

    def cast(self, value: Any, sql_type: str) -> Expression[Any]:
        is_array = sql_type.upper().endswith("[]")
        type_hint = list[str] if sql_type.upper() in {"VARCHAR[]", "TEXT[]"} else (list[Any] if is_array else Any)
        return Expression("cast", (to_expression(value), sql_type), type_hint, "collection" if is_array else "scalar")

    def deterministic_uuid(self, value: ExpressionInput[str]) -> Expression[str]:
        return Expression("uuid", (to_expression(value),), str)

    def struct_field[T](self, value: ValueRef[Any] | Expression[Any], name: str, *, as_type: type[T]) -> Expression[T]:
        validate_value_type(as_type, context="struct_field result", allow_collection=True)
        return Expression("struct_field", (to_expression(value), name), as_type, "collection" if item_type(as_type) is not None else "scalar")


value = ValueExpressions()
