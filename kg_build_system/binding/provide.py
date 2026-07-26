"""Portable expression construction."""
from __future__ import annotations
from typing import Any, Literal, overload

from ..expressions import Expression, FieldPath, item_type
from ..specification import Declaration

def normalise(value: Any) -> Expression[Any] | FieldPath[Any]:
    return value if isinstance(value, (Expression, FieldPath)) else Expression("literal", (value,), type(value))

class ValueExpressions:
    def concat(self, *values: Any) -> Expression[str]: return Expression("concat", tuple(normalise(value) for value in values), str)
    def coalesce(self, *values: Any) -> Expression[Any]:
        expressions = tuple(normalise(value) for value in values)
        return Expression("coalesce", expressions, expressions[0].type_hint if expressions else Any)
    @overload
    def cast(self, value: Declaration[list[str]] | Expression[list[str]] | FieldPath[list[str]], sql_type: Literal["VARCHAR[]", "TEXT[]"]) -> Expression[list[str]]: ...
    @overload
    def cast(self, value: Any, sql_type: str) -> Expression[Any]: ...
    def cast(self, value: Any, sql_type: str) -> Expression[Any]:
        is_text_array = sql_type.upper() in {"VARCHAR[]", "TEXT[]"}
        return Expression("cast", (normalise(value), sql_type), list[str] if is_text_array else Any, "collection" if is_text_array else "scalar")
    def deterministic_uuid(self, value: Any) -> Expression[str]: return Expression("uuid", (normalise(value),), str)

class CollectionExpressions:
    def expand[T](self, value: Declaration[list[T]] | Expression[list[T]] | FieldPath[list[T]]) -> Expression[T]:
        expression = normalise(value); element = item_type(expression.type_hint)
        if element is None: raise TypeError("expand requires a declared list[T] value")
        return Expression("expand", (expression,), element, "expanded")

class Provide:
    value = ValueExpressions()
    collection = CollectionExpressions()
    def __call__(self, value: Any) -> Expression[Any] | FieldPath[Any]: return normalise(value)

provide = Provide()
