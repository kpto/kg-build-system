"""Demo of the model_concept authoring and expression API."""

from typing import assert_type

from model_concept import (
    Array,
    BoolValueExpression,
    IntValueExpression,
    NullableDataType,
    NullableValueExpression,
    StrValueExpression,
    Struct,
    Table,
    ValueExpression,
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


# each / pick preserve specialized unit expression types
item = ExampleTable.struct_field.pick(lambda x: x.field_int).each()
assert_type(item, IntValueExpression)
assert_type(item.add(3), IntValueExpression)

from_array = ExampleTable.scores.each()
assert_type(from_array, IntValueExpression)
assert_type(from_array.add(1).sub(1), IntValueExpression)

# nullable struct → non-null unit field propagates null, stays specialized
maybe_flag = ExampleTable.struct_field.pick(lambda x: x.flag)
assert_type(maybe_flag, NullableValueExpression[bool, BoolValueExpression])
assert_type(maybe_flag.or_else(False).not_(), BoolValueExpression)
assert_type(maybe_flag.when_present().not_(), BoolValueExpression)

maybe_label = ExampleTable.struct_field.pick(lambda x: x.label)
assert_type(maybe_label, NullableValueExpression[str, StrValueExpression])
assert_type(maybe_label.or_else("").append("!"), StrValueExpression)
assert_type(maybe_label.when_present().prepend("id:"), StrValueExpression)

# nullable unit through nullable struct: still single Nullable[…], specialized
maybe_score = ExampleTable.struct_field.pick(lambda x: x.maybe_score)
assert_type(maybe_score, NullableValueExpression[int, IntValueExpression])
assert_type(maybe_score.or_else(0).add(3), IntValueExpression)
assert_type(maybe_score.when_present().add(3), IntValueExpression)

# table-level unit field is already specialized
assert_type(ExampleTable.name.prepend("[").append("]"), StrValueExpression)

expr = item.add(3)
result = accept_expression(expr)
