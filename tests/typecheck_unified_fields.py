"""Static contract for unified Field declarations; checked directly by Pyright."""
from typing import assert_type

from kg_build_system.expressions import (
    ArrayNullableValueExpression,
    ArrayValueExpression,
    BoolValueExpression,
    IntValueExpression,
    NullableValueExpression,
    StrValueExpression,
    StructNullableValueExpression,
    StructValueExpression,
)
from kg_build_system.table.fields import Field, field
from kg_build_system.table.models import Table
from kg_build_system.types import Array, Nullable, Struct


class EvidenceStruct(Struct):
    label: Field[str] = field()
    labels: Field[Array[str]] = field()


class DetailsStruct(Struct):
    flag: Field[bool] = field()
    label: Field[str] = field()
    score: Field[int | None] = field()
    evidence: Field[EvidenceStruct | None] = field()
    flags: Field[Array[bool | None] | None] = field()


class InputTable(Table):
    details: Field[DetailsStruct | None] = field()
    scores: Field[Array[int]] = field()
    evidence: Field[Array[EvidenceStruct]] = field()
    optional_scores: Field[Array[int] | None] = field()
    maybe_scores: Field[Array[int | None]] = field()
    name: Field[str] = field()


assert_type(InputTable.name, StrValueExpression)
assert_type(InputTable.name.prepend("[").append("]"), StrValueExpression)
assert_type(InputTable.scores, ArrayValueExpression[int, IntValueExpression])
assert_type(InputTable.scores.each().add(1), IntValueExpression)
assert_type(
    InputTable.optional_scores,
    ArrayNullableValueExpression[
        int, IntValueExpression, NullableValueExpression[int, IntValueExpression]
    ],
)
assert_type(InputTable.optional_scores.each().add(1), IntValueExpression)
assert_type(
    InputTable.maybe_scores.each(),
    NullableValueExpression[int, IntValueExpression],
)
assert_type(
    InputTable.evidence.each(),
    StructValueExpression[EvidenceStruct],
)
assert_type(
    InputTable.evidence.each().pick(lambda value: value.labels).each().append("!"),
    StrValueExpression,
)
assert_type(InputTable.details, StructNullableValueExpression[DetailsStruct])

maybe_flag = InputTable.details.pick(lambda value: value.flag)
assert_type(maybe_flag, NullableValueExpression[bool, BoolValueExpression])
assert_type(maybe_flag.or_else(False).not_(), BoolValueExpression)

maybe_score = InputTable.details.pick(lambda value: value.score)
assert_type(maybe_score, NullableValueExpression[int, IntValueExpression])
assert_type(maybe_score.when_present().add(1), IntValueExpression)

nested_label = InputTable.details.pick(lambda value: value.evidence).pick(
    lambda value: value.label
)
assert_type(nested_label, NullableValueExpression[str, StrValueExpression])

nullable_items = InputTable.details.pick(lambda value: value.flags).each()
assert_type(nullable_items, NullableValueExpression[bool, BoolValueExpression])

internal_nullable: object = Nullable[int]
