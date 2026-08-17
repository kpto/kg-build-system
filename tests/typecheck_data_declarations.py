"""Static contract for typed tables, structs, and projection selections."""
from typing import assert_type

from kg_build_system import (
    Array, ArraySelection, Field, IntExpression, NullableExpression,
    NullableSelection, Projection, StrExpression, Struct, StructSelection,
    Table, ValueSelection, field, projection_field,
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
        InputTable.details.pick(lambda details: details.label).default_to("unknown")
    )
    score = projection_field(InputTable.details.pick(lambda details: details.score))
    values = projection_field(InputTable.values)


assert_type(InputTable.details, NullableSelection[DetailsStruct])
assert_type(TypedProjection.identifier, ValueSelection[str])
assert_type(TypedProjection.identifier.expression, StrExpression)
assert_type(TypedProjection.label, ValueSelection[str])
assert_type(TypedProjection.score, NullableSelection[int])
assert_type(TypedProjection.score.expression, NullableExpression[int, IntExpression])
assert_type(TypedProjection.values, ArraySelection[int])
