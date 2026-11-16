"""A computed field carries access presence in its descriptor class."""
from __future__ import annotations

from kg_build_system import (
    Field,
    NullableComputedField,
    Omitted,
    computed_field,
    value_expression,
)
from kg_build_system.kernel import STR, NullableType


def test_a_present_computed_field_is_a_plain_field() -> None:
    descriptor = computed_field(value_expression("x"), meaning=Omitted)

    assert isinstance(descriptor, Field)
    assert not isinstance(descriptor, NullableComputedField)


def test_a_nullable_computed_field_is_a_nullable_descriptor() -> None:
    descriptor = computed_field(
        value_expression(None, logical_type=NullableType(STR)),
        meaning=Omitted,
    )

    assert isinstance(descriptor, NullableComputedField)
    assert type(descriptor) is NullableComputedField
