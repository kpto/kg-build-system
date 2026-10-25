"""Static contract for bindable calculations and terminal normalization."""
from typing import assert_type, cast

from kg_build_system.expressions import (
    ArrayExpression, ArraySelection, BoolExpression, IntExpression,
    NullableExpression, NullableSelection, StrExpression, ValueExpression,
    ValueInput, ValueSelection, as_expression, select_expression,
)
from kg_build_system.expressions.literals import literal
from kg_build_system.types import Array, ArrayType, INT, Nullable, NullableType, STR


integer = IntExpression(literal(1))
assert_type(integer.add(2).sub(1), IntExpression)

text = StrExpression(literal("value"))
assert_type(text.prepend("[").append("]"), StrExpression)
assert_type(text.to_string(), StrExpression)
assert_type(integer.to_string(), StrExpression)
assert_type(text.equals("value"), BoolExpression)
assert_type(text.replace(":", "_"), StrExpression)
assert_type(text.before_separator(":", 2), StrExpression)
assert_type(
    text.after_separator(":", 2, include_separator=True), StrExpression,
)

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
assert_type(
    nullable_expression.to_string(), NullableExpression[str, StrExpression],
)

text_selection = select_expression(text)
assert_type(text_selection.expression.before_separator(":"), StrExpression)
assert_type(text_selection.expression.after_separator(":", 2), StrExpression)

array_selection = cast(ArraySelection[int], select_expression(array_expression))
assert_type(array_selection.expand(), ValueSelection[int])
assert_type(array_selection.expand().expression.add(1), IntExpression)
assert_type(
    array_expression.transform_items(lambda item: item.to_string()),
    ArrayExpression[str],
)
assert_type(array_selection.drop_null_items(), ArraySelection[int])
assert_type(array_selection.sort(), ArraySelection[int])
assert_type(array_selection.distinct(), ArraySelection[int])

string_array = ArrayExpression[str](literal(["a"], logical_type=ArrayType(STR)))
string_selection = cast(ArraySelection[str], select_expression(string_array))
assert_type(string_selection.join(","), ValueSelection[str])

flag = BoolExpression(literal(True))
assert_type(flag.not_().and_(False), BoolExpression)

selection_input: ValueInput[int] = array_selection.expand()
expression_input: ValueInput[int] = integer
assert_type(as_expression(selection_input), ValueExpression[int])
assert_type(as_expression(expression_input), ValueExpression[int])

accepts_internal_nullable: object = cast(Nullable[int], object())
accepts_array: object = cast(Array[int], object())
