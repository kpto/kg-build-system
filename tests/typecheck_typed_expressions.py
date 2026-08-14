"""Static contract for the typed expression families; checked directly by Pyright."""
from typing import assert_type, cast

from kg_build_system.expressions import (
    ArrayNullableValueExpression,
    ArrayValueExpression,
    BoolValueExpression,
    IntValueExpression,
    NullableValueExpression,
    StrValueExpression,
)
from kg_build_system.expressions.literals import literal
from kg_build_system.types import Array, ArrayType, INT, Nullable, NullableType, STR


integer = IntValueExpression(literal(1))
assert_type(integer.add(2).sub(1), IntValueExpression)

text = StrValueExpression(literal("value"))
assert_type(text.prepend("[").append("]"), StrValueExpression)

nullable = cast(
    NullableValueExpression[int, IntValueExpression],
    NullableValueExpression(literal(None, logical_type=NullableType(INT)), IntValueExpression),
)
assert_type(nullable, NullableValueExpression[int, IntValueExpression])
assert_type(nullable.or_else(0).add(1), IntValueExpression)
assert_type(nullable.when_present().sub(1), IntValueExpression)

array = ArrayValueExpression[int, IntValueExpression](
    literal([1], logical_type=ArrayType(INT))
)
assert_type(array, ArrayValueExpression[int, IntValueExpression])
assert_type(array.each().add(1), IntValueExpression)

nullable_array = ArrayNullableValueExpression[int, IntValueExpression, NullableValueExpression[int, IntValueExpression]](
    literal(None, logical_type=NullableType(ArrayType(INT)))
)
assert_type(nullable_array.each(), IntValueExpression)
assert_type(nullable_array.or_else(array), ArrayValueExpression[int, IntValueExpression])

flag = BoolValueExpression(literal(True))
assert_type(flag.not_().and_(False), BoolValueExpression)

accepts_internal_nullable: object = cast(Nullable[int], object())
accepts_array: object = cast(Array[int], object())
