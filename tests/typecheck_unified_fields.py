"""Static contract for the unified field model and source-field nullability."""
import datetime
from typing import assert_type
from uuid import UUID

from kg_build_system import ComputedStruct, Projection, Table
from kg_build_system.expressions import (
    ArraySelection, BoolExpression, IntExpression, NullableExpression,
    NullableSelection, StrExpression, StructSelection, ValueExpression,
    ValueSelection, value_expression,
)
from kg_build_system.table.fields import Field, computed_field, field
from kg_build_system.table.models import Struct
from kg_build_system.types import Array, Date, Nullable, Time, Timestamp, Uuid


class EvidenceStruct(Struct):
    label: Field[str] = field()
    labels: Field[Array[str]] = field()


class DetailsStruct(Struct):
    label: Field[str] = field()
    flag: Field[bool] = field()
    score: Field[int | None] = field()
    evidence: Field[EvidenceStruct] = field()
    flags: Field[Array[bool | None]] = field()


class InputTable(Table):
    details: Field[DetailsStruct] = field()
    scores: Field[Array[int]] = field()
    evidence: Field[Array[EvidenceStruct]] = field()
    optional_scores: Field[Array[int] | None] = field()
    maybe_scores: Field[Array[int | None]] = field()
    name: Field[str] = field()


# Every source field is nullable on access, whatever its value type says.
assert_type(InputTable.name, NullableSelection[str])
assert_type(InputTable.name.alter_rows().drop_null(), ValueSelection[str])
assert_type(InputTable.name.alter_rows().drop_null().expression, StrExpression)
assert_type(InputTable.scores, NullableSelection[Array[int]])
assert_type(InputTable.scores.alter_rows().drop_null(), ArraySelection[int])
assert_type(
    InputTable.scores.alter_rows().drop_null().expand(), ValueSelection[int],
)
assert_type(
    InputTable.scores.alter_rows().drop_null().expand().expression, IntExpression,
)
assert_type(InputTable.optional_scores, NullableSelection[Array[int]])
assert_type(InputTable.maybe_scores, NullableSelection[Array[Nullable[int]]])
assert_type(
    InputTable.maybe_scores.alter_rows().drop_null().expand(),
    NullableSelection[int],
)
assert_type(
    InputTable.maybe_scores.alter_rows().drop_null().expand().expression,
    NullableExpression[int, IntExpression],
)
assert_type(InputTable.evidence, NullableSelection[Array[EvidenceStruct]])
assert_type(
    InputTable.evidence.alter_rows().drop_null().expand(),
    StructSelection[EvidenceStruct],
)
assert_type(InputTable.details, NullableSelection[DetailsStruct])
assert_type(
    InputTable.details.extract(lambda value: value.label),
    NullableSelection[str],
)
assert_type(
    InputTable.details.extract(lambda value: value.flag), NullableSelection[bool],
)
assert_type(
    InputTable.details.extract(lambda value: value.flag).default_to(False),
    ValueSelection[bool],
)
assert_type(
    InputTable.details.extract(lambda value: value.flag).default_to(False).expression.not_(),
    BoolExpression,
)
assert_type(
    InputTable.details.extract(lambda value: value.score).alter_rows().drop_null(),
    ValueSelection[int],
)
assert_type(
    InputTable.details.extract(lambda value: value.evidence),
    NullableSelection[EvidenceStruct],
)
assert_type(
    InputTable.details.extract(lambda value: value.flags).alter_rows().expand(),
    NullableSelection[bool],
)


class ComputedRecord(ComputedStruct):
    label = computed_field(InputTable.name.alter_rows().drop_null())
    maybe = computed_field(InputTable.details.extract(lambda value: value.flag))


assert_type(ComputedRecord.label, ValueSelection[str])
assert_type(ComputedRecord.maybe, NullableSelection[bool])


class Projected(Projection(InputTable.row_source())):
    label = computed_field(
        InputTable.details.extract(lambda value: value.label)
        .alter_rows().drop_null()
    )
    maybe = computed_field(InputTable.details.extract(lambda value: value.label))


assert_type(Projected.label, ValueSelection[str])
assert_type(Projected.label.expression, StrExpression)
assert_type(Projected.maybe, NullableSelection[str])
assert_type(
    Projected.maybe.expression, NullableExpression[str, StrExpression],
)


class TemporalTable(Table):
    """Representative and stdlib spellings are one declaration, so they select alike."""

    on: Field[Date] = field()
    at: Field[Time | None] = field()
    recorded: Field[Timestamp] = field()
    token: Field[Uuid] = field()
    stdlib_on: Field[datetime.date | None] = field()
    stdlib_at: Field[datetime.time] = field()
    stdlib_recorded: Field[datetime.datetime] = field()
    stdlib_token: Field[UUID] = field()


assert_type(TemporalTable.on, NullableSelection[Date])
assert_type(TemporalTable.on.alter_rows().drop_null().expression, ValueExpression[Date])
assert_type(TemporalTable.at, NullableSelection[Time])
assert_type(TemporalTable.at.alter_rows().drop_null(), ValueSelection[Time])
assert_type(TemporalTable.at.default_to(datetime.time(9, 30)), ValueSelection[Time])
assert_type(TemporalTable.recorded, NullableSelection[Timestamp])
assert_type(TemporalTable.token, NullableSelection[Uuid])


class ReadingTable(Table):
    taken_at: Field[Array[Timestamp]] = field()
    observed_on: Field[Array[Date | None]] = field()


assert_type(ReadingTable.taken_at, NullableSelection[Array[Timestamp]])
assert_type(
    ReadingTable.taken_at.alter_rows().drop_null().expand(), ValueSelection[Timestamp],
)
assert_type(
    ReadingTable.observed_on.alter_rows().expand(), NullableSelection[Date],
)
