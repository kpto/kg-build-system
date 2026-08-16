"""Demo of the model_concept authoring and expression API."""

from typing import assert_type

from model_concept import (
    Array,
    ArrayExpression,
    ArraySelection,
    BoolExpression,
    IntExpression,
    NullableDataType,
    NullableExpression,
    NullableSelection,
    StrExpression,
    Struct,
    StructSelection,
    Table,
    ValueExpression,
    ValueSelection,
)
from model_concept_field import Field, field


class ExampleStruct(Struct):
    field_int: Field[Array[int]] = field()
    flag: Field[bool] = field()
    label: Field[str] = field()
    maybe_score: Field[int | None] = field()


class ExampleTable(Table):
    struct_field: Field[ExampleStruct | None] = field()
    scores: Field[Array[int]] = field()
    name: Field[str] = field()


def accept_expression[TType: NullableDataType](
    expr: ValueExpression[TType],
) -> TType: ...


def accept_selection[TType: NullableDataType](selection: ValueSelection[TType]) -> None: ...


# Field → selection specialization by shape; .expression exposes a specialized
# bindable calculation.
assert_type(ExampleTable.struct_field, NullableSelection[ExampleStruct])
assert_type(ExampleTable.scores, ArraySelection[int])
assert_type(ExampleTable.name, ValueSelection[str])
assert_type(ExampleTable.scores.expression, ArrayExpression[int])
assert_type(ExampleTable.name.expression, StrExpression)

accept_selection(ExampleTable.name)
accept_selection(ExampleTable.scores)
accept_selection(ExampleTable.struct_field)

# Struct/array selections expose pick/expand; unit results remain generic
# ValueSelection[T].
item_selection = ExampleTable.struct_field.pick(lambda x: x.field_int).expand()
assert_type(item_selection, ValueSelection[int])
assert_type(item_selection.expression, IntExpression)
assert_type(item_selection.expression.add(3), IntExpression)

from_array = ExampleTable.scores.expand()
assert_type(from_array, ValueSelection[int])
assert_type(from_array.expression.add(1).sub(1), IntExpression)

# Null handling on NullableSelection
maybe_flag = ExampleTable.struct_field.pick(lambda x: x.flag)
assert_type(maybe_flag, NullableSelection[bool])
assert_type(maybe_flag.default_to(False), ValueSelection[bool])
assert_type(maybe_flag.default_to(False).expression.not_(), BoolExpression)
assert_type(maybe_flag.where_present(), ValueSelection[bool])
assert_type(maybe_flag.where_present().expression.not_(), BoolExpression)

maybe_label = ExampleTable.struct_field.pick(lambda x: x.label)
assert_type(maybe_label, NullableSelection[str])
assert_type(maybe_label.default_to("").expression.append("!"), StrExpression)
assert_type(maybe_label.where_present().expression.prepend("id:"), StrExpression)

maybe_score = ExampleTable.struct_field.pick(lambda x: x.maybe_score)
assert_type(maybe_score, NullableSelection[int])
assert_type(maybe_score.default_to(0).expression.add(3), IntExpression)
assert_type(maybe_score.where_present().expression.add(3), IntExpression)
assert_type(maybe_score.expression, NullableExpression[int, IntExpression])

# Picking an array beneath a nullable struct produces a nullable selection.
array_under_null = ExampleTable.struct_field.pick(lambda x: x.field_int)
assert_type(array_under_null, NullableSelection[Array[int]])
assert_type(array_under_null.expand(), ValueSelection[int])

assert_type(
    ExampleTable.name.expression.prepend("[").append("]"),
    StrExpression,
)

expr = (
    ExampleTable.struct_field.pick(lambda x: x.field_int).expand().expression.add(3)
)
result = accept_expression(expr)
