"""The 0-based array index operation."""
from __future__ import annotations

from ...types.interfaces import INT, ArrayType, NullableType, non_nullable
from ._predicates import is_array, is_exact
from .spec import ArgumentSpec, OperationSpec


def _result(types, parameters):
    array = non_nullable(types[0])
    assert isinstance(array, ArrayType)
    return array.item if isinstance(array.item, NullableType) else NullableType(array.item)


ARRAY_AT = OperationSpec(
    name="array_at",
    arity=2,
    arguments=(
        ArgumentSpec(accepts=is_array, description="array value"),
        ArgumentSpec(expected=INT, accepts=is_exact(INT), description="integer index"),
    ),
    result_type=_result,
)


__all__ = ["ARRAY_AT"]
