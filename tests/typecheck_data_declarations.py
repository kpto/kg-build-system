"""Static contract for typed tables, structs, and projection selections."""
from typing import assert_type

from kg_build_system import (
    Array, Field, IntExpression, NullableExpression, NullableSelection,
    Projection, StrExpression, Struct, Table, ValueSelection, computed_field,
    field,
)


class DetailsStruct(Struct):
    label: Field[str] = field()
    score: Field[int | None] = field()


class InputTable(Table):
    identifier: Field[str] = field()
    details: Field[DetailsStruct | None] = field()
    values: Field[Array[int]] = field()


class TypedProjection(Projection(InputTable.row_source())):
    identifier = computed_field(InputTable.identifier)
    label = computed_field(
        InputTable.details.extract(lambda details: details.label).default_to("unknown")
    )
    score = computed_field(InputTable.details.extract(lambda details: details.score))
    values = computed_field(InputTable.values)


# A source field is nullable on access, so a projection that reproduces it is
# nullable too; explicit narrowing makes the output typed.
assert_type(InputTable.details, NullableSelection[DetailsStruct])
assert_type(TypedProjection.identifier, NullableSelection[str])
assert_type(
    TypedProjection.identifier.expression, NullableExpression[str, StrExpression],
)
assert_type(TypedProjection.label, ValueSelection[str])
assert_type(TypedProjection.score, NullableSelection[int])
assert_type(TypedProjection.score.expression, NullableExpression[int, IntExpression])
assert_type(TypedProjection.values, NullableSelection[Array[int]])
