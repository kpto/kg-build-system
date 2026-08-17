"""Static contract for bindable calculations and terminal normalization."""
from typing import assert_type, cast

from kg_build_system.expressions import (
    ArrayExpression, ArraySelection, BoolExpression, IntExpression,
    NullableExpression, NullableSelection, StrExpression, ValueExpression,
    ValueInput, ValueSelection, as_expression, select_expression,
)
from kg_build_system.expressions.literals import literal
from kg_build_system.types import Array, ArrayType, INT, Nullable, NullableType


integer = IntExpression(literal(1))
assert_type(integer.add(2).sub(1), IntExpression)

text = StrExpression(literal("value"))
assert_type(text.prepend("[").append("]"), StrExpression)

nullable_expression = cast(
    NullableExpression[int, IntExpression],
    NullableExpression(literal(None, logical_type=NullableType(INT)), IntExpression),
)
assert_type(nullable_expression, NullableExpression[int, IntExpression])

array_expression = ArrayExpression[int](literal([1], logical_type=ArrayType(INT)))
assert_type(array_expression, ArrayExpression[int])

nullable_selection = cast(
    NullableSelection[int],
    select_expression(nullable_expression),
)
assert_type(nullable_selection.default_to(0).expression.add(1), IntExpression)
assert_type(nullable_selection.where_present().expression.sub(1), IntExpression)

array_selection = cast(ArraySelection[int], select_expression(array_expression))
assert_type(array_selection.expand(), ValueSelection[int])
assert_type(array_selection.expand().expression.add(1), IntExpression)

flag = BoolExpression(literal(True))
assert_type(flag.not_().and_(False), BoolExpression)

selection_input: ValueInput[int] = array_selection.expand()
expression_input: ValueInput[int] = integer
assert_type(as_expression(selection_input), ValueExpression[int])
assert_type(as_expression(expression_input), ValueExpression[int])

accepts_internal_nullable: object = cast(Nullable[int], object())
accepts_array: object = cast(Array[int], object())
