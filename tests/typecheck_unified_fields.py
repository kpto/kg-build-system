"""Static contract for selection-specialized unified fields."""
from typing import assert_type

from kg_build_system.expressions import (
    ArrayExpression, ArraySelection, BoolExpression, IntExpression,
    NullableExpression, NullableSelection, StrExpression, StructExpression,
    StructSelection, ValueSelection,
)
from kg_build_system.table.fields import Field, field
from kg_build_system.table.models import Struct, Table
from kg_build_system.types import Array, Nullable


class EvidenceStruct(Struct):
    label: Field[str] = field()
    labels: Field[Array[str]] = field()


class DetailsStruct(Struct):
    flag: Field[bool] = field()
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


assert_type(InputTable.name, ValueSelection[str])
assert_type(InputTable.name.expression, StrExpression)
assert_type(InputTable.name.expression.prepend("[").append("]"), StrExpression)
assert_type(InputTable.scores, ArraySelection[int])
assert_type(InputTable.scores.expression, ArrayExpression[int])
assert_type(InputTable.scores.expand(), ValueSelection[int])
assert_type(InputTable.scores.expand().expression.add(1), IntExpression)
assert_type(InputTable.optional_scores, NullableSelection[Array[int]])
assert_type(InputTable.optional_scores.expand(), ValueSelection[int])
assert_type(InputTable.maybe_scores.expand(), NullableSelection[int])
assert_type(InputTable.maybe_scores.expand().expression, NullableExpression[int, IntExpression])
assert_type(InputTable.evidence.expand(), StructSelection[EvidenceStruct])
assert_type(InputTable.evidence.expand().expression, StructExpression[EvidenceStruct])
assert_type(
    InputTable.evidence.expand().pick(lambda value: value.labels).expand().expression.append("!"),
    StrExpression,
)
assert_type(InputTable.details, NullableSelection[DetailsStruct])

maybe_flag = InputTable.details.pick(lambda value: value.flag)
assert_type(maybe_flag, NullableSelection[bool])
assert_type(maybe_flag.expression, NullableExpression[bool, BoolExpression])
assert_type(maybe_flag.default_to(False), ValueSelection[bool])
assert_type(maybe_flag.default_to(False).expression.not_(), BoolExpression)

maybe_score = InputTable.details.pick(lambda value: value.score)
assert_type(maybe_score, NullableSelection[int])
assert_type(maybe_score.where_present(), ValueSelection[int])
assert_type(maybe_score.where_present().expression.add(1), IntExpression)

nested = InputTable.details.pick(lambda value: value.evidence)
assert_type(nested, NullableSelection[EvidenceStruct])
assert_type(nested.pick(lambda value: value.label), NullableSelection[str])
assert_type(
    InputTable.details.pick(lambda value: value.flags).expand(),
    NullableSelection[bool],
)

internal_nullable: object = Nullable[int]
