"""Static contract for typed tables, structs, and projection outputs."""
from typing import assert_type

from kg_build_system import (
    Array,
    ArrayValueExpression,
    Field,
    IntValueExpression,
    NullableValueExpression,
    Projection,
    StrValueExpression,
    Struct,
    StructNullableValueExpression,
    Table,
    field,
    projection_field,
)


class DetailsStruct(Struct):
    label: Field[str] = field()
    score: Field[int | None] = field()


class InputTable(Table):
    identifier: Field[str] = field()
    details: Field[DetailsStruct | None] = field()
    values: Field[Array[int]] = field()


class TypedProjection(Projection):
    identifier = projection_field(InputTable.identifier)
    label = projection_field(
        InputTable.details.pick(lambda details: details.label).or_else("unknown")
    )
    score = projection_field(
        InputTable.details.pick(lambda details: details.score)
    )
    values = projection_field(InputTable.values)


assert_type(InputTable.details, StructNullableValueExpression[DetailsStruct])
assert_type(TypedProjection.identifier, StrValueExpression)
assert_type(TypedProjection.label, StrValueExpression)
assert_type(
    TypedProjection.score,
    NullableValueExpression[int, IntValueExpression],
)
assert_type(
    TypedProjection.values,
    ArrayValueExpression[int, IntValueExpression],
)
