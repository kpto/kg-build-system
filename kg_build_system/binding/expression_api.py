"""Portable expression constructors used by graph bindings."""
from __future__ import annotations
from typing import Any, Literal, overload

from ..expressions import Expression, FieldPath, item_type
from .models import ExpressionBinding

type ExpressionInput[T] = T | FieldPath[T] | Expression[T]

def _to_expression(value: Any) -> Expression[Any]:
    if isinstance(value, Expression): return value
    if isinstance(value, FieldPath): return Expression("field", (value,), value.type_hint, value.cardinality)
    return Expression("literal", (value,), type(value))

def bind[T](value: ExpressionInput[T]) -> ExpressionBinding[T]:
    """Create a typed value binding for a graph property slot."""
    return ExpressionBinding(expression=_to_expression(value))

class ValueExpressions:
    def literal[T](self, value: T) -> Expression[T]:
        return _to_expression(value)
    def concat(self, *values: Any) -> Expression[str]: return Expression("concat", tuple(_to_expression(value) for value in values), str)
    def coalesce(self, *values: Any) -> Expression[Any]:
        expressions = tuple(_to_expression(value) for value in values)
        return Expression("coalesce", expressions, expressions[0].type_hint if expressions else Any)
    @overload
    def cast(self, value: FieldPath[list[str]] | Expression[list[str]], sql_type: Literal["VARCHAR[]", "TEXT[]"]) -> Expression[list[str]]: ...
    @overload
    def cast(self, value: Any, sql_type: str) -> Expression[Any]: ...
    def cast(self, value: Any, sql_type: str) -> Expression[Any]:
        is_array = sql_type.upper().endswith("[]")
        return Expression("cast", (_to_expression(value), sql_type), list[str] if sql_type.upper() in {"VARCHAR[]", "TEXT[]"} else (list[Any] if is_array else Any), "collection" if is_array else "scalar")
    def deterministic_uuid(self, value: Any) -> Expression[str]: return Expression("uuid", (_to_expression(value),), str)
    def struct_field[T](self, value: Any, name: str, *, as_type: type[T]) -> Expression[T]: return Expression("struct_field", (_to_expression(value), name), as_type, "collection" if item_type(as_type) is not None else "scalar")

class LookupExpressions:
    def one[T](self, *, key: Any, match: Any, value: Any, as_type: type[T]) -> Expression[T]: return Expression("lookup_one", (_to_expression(key), _to_expression(match), _to_expression(value)), as_type)

class CollectionExpressions:
    @overload
    def expand[E](self, value: FieldPath[list[E]] | Expression[list[E]]) -> Expression[E]: ...
    @overload
    def expand[T](self, value: Expression[T] | FieldPath[T]) -> Expression[T]: ...
    def expand(self, value: Any) -> Expression[Any]:
        expression = _to_expression(value); element = item_type(expression.type_hint)
        if element is None and expression.cardinality != "collection": raise TypeError("expand requires a declared list[T] value")
        return Expression("expand", (expression,), element or expression.type_hint, "expanded")

value = ValueExpressions()
collection = CollectionExpressions()
lookup = LookupExpressions()
