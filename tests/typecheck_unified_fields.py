"""Static contract for unified Field declarations; checked directly by Pyright."""
from typing import assert_type

from kg_build_system.expressions import (
    ArrayValueExpression,
    BoolValueExpression,
    IntValueExpression,
    NullableValueExpression,
    StrValueExpression,
    StructNullableValueExpression,
)
from kg_build_system.table.fields import Field, field
from kg_build_system.table.models import Table
from kg_build_system.types import Array, Nullable, Struct


class DetailsStruct(Struct):
    flag: Field[bool] = field()
    label: Field[str] = field()
    score: Field[int | None] = field()


class InputTable(Table):
    details: Field[DetailsStruct | None] = field()
    scores: Field[Array[int]] = field()
    name: Field[str] = field()


assert_type(InputTable.name, StrValueExpression)
assert_type(InputTable.name.prepend("[").append("]"), StrValueExpression)
assert_type(InputTable.scores, ArrayValueExpression[int, IntValueExpression])
assert_type(InputTable.scores.each().add(1), IntValueExpression)
assert_type(InputTable.details, StructNullableValueExpression[DetailsStruct])

maybe_flag = InputTable.details.pick(lambda value: value.flag)
assert_type(maybe_flag, NullableValueExpression[bool, BoolValueExpression])
assert_type(maybe_flag.or_else(False).not_(), BoolValueExpression)

maybe_score = InputTable.details.pick(lambda value: value.score)
assert_type(maybe_score, NullableValueExpression[int, IntValueExpression])
assert_type(maybe_score.when_present().add(1), IntValueExpression)

internal_nullable: object = Nullable[int]
