"""Scalar portable expression constructors."""
from collections.abc import Sequence
from types import NoneType
from typing import Any, Literal, overload

from .._support.annotations import type_shape
from ..data_types import Scalar, Struct, validate_value_type
from .core import Expression, ExpressionValue, PermittedExpressionValue, ValueRef, item_type
from .inputs import ExpressionInput, to_expression

type TextSqlType = Literal["TEXT", "VARCHAR"]
type BooleanSqlType = Literal["BOOL", "BOOLEAN"]
type IntegerSqlType = Literal["TINYINT", "SMALLINT", "INTEGER", "INT", "BIGINT", "HUGEINT", "UBIGINT"]
type FloatSqlType = Literal["REAL", "FLOAT", "DOUBLE"]
type TextArraySqlType = Literal["TEXT[]", "VARCHAR[]"]
type BooleanArraySqlType = Literal["BOOL[]", "BOOLEAN[]"]
type IntegerArraySqlType = Literal["TINYINT[]", "SMALLINT[]", "INTEGER[]", "INT[]", "BIGINT[]", "HUGEINT[]", "UBIGINT[]"]
type FloatArraySqlType = Literal["REAL[]", "FLOAT[]", "DOUBLE[]"]
type SupportedSqlType = TextSqlType | BooleanSqlType | IntegerSqlType | FloatSqlType | TextArraySqlType | BooleanArraySqlType | IntegerArraySqlType | FloatArraySqlType
type StructFieldValue = Scalar | Sequence[Scalar | None] | None


_CAST_TYPES: dict[str, type | Any] = {
    **{name: str for name in ("TEXT", "VARCHAR")},
    **{name: bool for name in ("BOOL", "BOOLEAN")},
    **{name: int for name in ("TINYINT", "SMALLINT", "INTEGER", "INT", "BIGINT", "HUGEINT", "UBIGINT")},
    **{name: float for name in ("REAL", "FLOAT", "DOUBLE")},
    **{f"{name}[]": list[item] for name, item in {
        "TEXT": str, "VARCHAR": str, "BOOL": bool, "BOOLEAN": bool,
        "TINYINT": int, "SMALLINT": int, "INTEGER": int, "INT": int,
        "BIGINT": int, "HUGEINT": int, "UBIGINT": int,
        "REAL": float, "FLOAT": float, "DOUBLE": float,
    }.items()},
}
_MISSING = object()


class ValueExpressions:
    def literal[T: Scalar | Sequence[Scalar | None] | None](self, value: T) -> Expression[T]:
        return to_expression(value)

    def concat(self, value: ExpressionInput[str], *values: ExpressionInput[str]) -> Expression[str]:
        return Expression("concat", tuple(to_expression(item) for item in (value, *values)), str)

    @overload
    def coalesce[T: ExpressionValue[PermittedExpressionValue]](self, value: ExpressionInput[T | None], fallback: ExpressionInput[T], *values: ExpressionInput[T]) -> Expression[T]: ...

    @overload
    def coalesce[T: ExpressionValue[PermittedExpressionValue]](self, value: ExpressionInput[T], *values: ExpressionInput[T]) -> Expression[T]: ...

    def coalesce(self, value: Any, fallback: Any = _MISSING, *values: Any) -> Expression[Any]:
        items = (value,) if fallback is _MISSING else (value, fallback, *values)
        expressions = tuple(to_expression(item) for item in items)
        non_null = next((item.type_hint for item in expressions if item.type_hint is not NoneType and not type_shape(item.type_hint).nullable), None)
        return Expression("coalesce", expressions, non_null or expressions[0].type_hint)

    @overload
    def cast(self, value: ExpressionInput[PermittedExpressionValue], sql_type: TextSqlType) -> Expression[str]: ...

    @overload
    def cast(self, value: ExpressionInput[PermittedExpressionValue], sql_type: BooleanSqlType) -> Expression[bool]: ...

    @overload
    def cast(self, value: ExpressionInput[PermittedExpressionValue], sql_type: IntegerSqlType) -> Expression[int]: ...

    @overload
    def cast(self, value: ExpressionInput[PermittedExpressionValue], sql_type: FloatSqlType) -> Expression[float]: ...

    @overload
    def cast(self, value: ExpressionInput[PermittedExpressionValue], sql_type: TextArraySqlType) -> Expression[Sequence[str]]: ...

    @overload
    def cast(self, value: ExpressionInput[PermittedExpressionValue], sql_type: BooleanArraySqlType) -> Expression[Sequence[bool]]: ...

    @overload
    def cast(self, value: ExpressionInput[PermittedExpressionValue], sql_type: IntegerArraySqlType) -> Expression[Sequence[int]]: ...

    @overload
    def cast(self, value: ExpressionInput[PermittedExpressionValue], sql_type: FloatArraySqlType) -> Expression[Sequence[float]]: ...

    def cast(self, value: ExpressionInput[PermittedExpressionValue], sql_type: SupportedSqlType) -> Expression[ExpressionValue]:
        normalized = sql_type.upper()
        if normalized not in _CAST_TYPES:
            raise ValueError(f"unsupported SQL cast type {sql_type!r}")
        type_hint = _CAST_TYPES[normalized]
        return Expression("cast", (to_expression(value), normalized), type_hint, "collection" if normalized.endswith("[]") else "scalar")

    def deterministic_uuid(self, value: ExpressionInput[str]) -> Expression[str]:
        return Expression("uuid", (to_expression(value),), str)

    def struct_field[S: Struct, T: StructFieldValue](self, value: ValueRef[S] | Expression[S], name: str, *, as_type: type[T]) -> Expression[T]:
        validate_value_type(as_type, context="struct_field result", allow_collection=True)
        return Expression("struct_field", (to_expression(value), name), as_type, "collection" if item_type(as_type) is not None else "scalar")


value = ValueExpressions()
