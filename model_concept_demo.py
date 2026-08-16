"""Demo of the model_concept authoring and expression API."""

from typing import assert_type

from model_concept import (
    Array,
    ArrayValueExpression,
    ArrayValuePlan,
    BoolValueExpression,
    IntValueExpression,
    NullableDataType,
    NullableValueExpression,
    NullableValuePlan,
    StrValueExpression,
    Struct,
    StructValuePlan,
    Table,
    ValueExpression,
    ValuePlan,
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


def accept_plan[TType: NullableDataType](plan: ValuePlan[TType]) -> None: ...


# Field → plan specialisation by shape; .value specialises the expression
assert_type(ExampleTable.struct_field, NullableValuePlan[ExampleStruct])
assert_type(ExampleTable.scores, ArrayValuePlan[int])
assert_type(ExampleTable.name, ValuePlan[str])
assert_type(ExampleTable.scores.value, ArrayValueExpression[int])
assert_type(ExampleTable.name.value, StrValueExpression)

accept_plan(ExampleTable.name)
accept_plan(ExampleTable.scores)
accept_plan(ExampleTable.struct_field)

# Struct/Array plans expose pick/each; result plans stay generic ValuePlan[T] for units
item_plan = ExampleTable.struct_field.pick(lambda x: x.field_int).each()
assert_type(item_plan, ValuePlan[int])
assert_type(item_plan.value, IntValueExpression)
assert_type(item_plan.value.add(3), IntValueExpression)

from_array = ExampleTable.scores.each()
assert_type(from_array, ValuePlan[int])
assert_type(from_array.value.add(1).sub(1), IntValueExpression)

# Null handling on NullableValuePlan
maybe_flag = ExampleTable.struct_field.pick(lambda x: x.flag)
assert_type(maybe_flag, NullableValuePlan[bool])
assert_type(maybe_flag.or_else(False), ValuePlan[bool])
assert_type(maybe_flag.or_else(False).value.not_(), BoolValueExpression)
assert_type(maybe_flag.when_present(), ValuePlan[bool])
assert_type(maybe_flag.when_present().value.not_(), BoolValueExpression)

maybe_label = ExampleTable.struct_field.pick(lambda x: x.label)
assert_type(maybe_label, NullableValuePlan[str])
assert_type(maybe_label.or_else("").value.append("!"), StrValueExpression)
assert_type(maybe_label.when_present().value.prepend("id:"), StrValueExpression)

maybe_score = ExampleTable.struct_field.pick(lambda x: x.maybe_score)
assert_type(maybe_score, NullableValuePlan[int])
assert_type(maybe_score.or_else(0).value.add(3), IntValueExpression)
assert_type(maybe_score.when_present().value.add(3), IntValueExpression)
assert_type(maybe_score.value, NullableValueExpression[int, IntValueExpression])

# pick of array field under nullable struct → NullableValuePlan[Array[int]]
array_under_null = ExampleTable.struct_field.pick(lambda x: x.field_int)
assert_type(array_under_null, NullableValuePlan[Array[int]])
assert_type(array_under_null.each(), ValuePlan[int])

assert_type(
    ExampleTable.name.value.prepend("[").append("]"),
    StrValueExpression,
)

expr = (
    ExampleTable.struct_field.pick(lambda x: x.field_int).each().value.add(3)
)
result = accept_expression(expr)
