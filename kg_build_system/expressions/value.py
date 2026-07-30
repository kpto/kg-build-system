"""Scalar portable expression constructors."""
from typing import Any, Literal, overload

from .core import Expression, FieldPath, item_type
from .inputs import to_expression


class ValueExpressions:
    def literal[T](self, value: T) -> Expression[T]:
        return to_expression(value)

    def concat(self, *values: Any) -> Expression[str]:
        return Expression("concat", tuple(to_expression(value) for value in values), str)

    def coalesce(self, *values: Any) -> Expression[Any]:
        expressions = tuple(to_expression(value) for value in values)
        return Expression("coalesce", expressions, expressions[0].type_hint if expressions else Any)

    @overload
    def cast(self, value: FieldPath[list[str]] | Expression[list[str]], sql_type: Literal["VARCHAR[]", "TEXT[]"]) -> Expression[list[str]]: ...

    @overload
    def cast(self, value: Any, sql_type: str) -> Expression[Any]: ...

    def cast(self, value: Any, sql_type: str) -> Expression[Any]:
        is_array = sql_type.upper().endswith("[]")
        type_hint = list[str] if sql_type.upper() in {"VARCHAR[]", "TEXT[]"} else (list[Any] if is_array else Any)
        return Expression("cast", (to_expression(value), sql_type), type_hint, "collection" if is_array else "scalar")

    def deterministic_uuid(self, value: Any) -> Expression[str]:
        return Expression("uuid", (to_expression(value),), str)

    def struct_field[T](self, value: Any, name: str, *, as_type: type[T]) -> Expression[T]:
        return Expression("struct_field", (to_expression(value), name), as_type, "collection" if item_type(as_type) is not None else "scalar")


value = ValueExpressions()
