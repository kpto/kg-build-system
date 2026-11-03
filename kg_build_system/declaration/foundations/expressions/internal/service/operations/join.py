"""The array-to-text join operation."""
from __future__ import annotations

from .......kernel.internal.types import STR, NullableType
from ._predicates import is_array_of, is_exact, is_non_null_unit
from .spec import ArgumentSpec, OperationSpec


def _result(types, parameters):
    return NullableType(STR) if isinstance(types[0], NullableType) else STR


JOIN = OperationSpec(
    name="join",
    arity=2,
    arguments=(
        ArgumentSpec(accepts=is_array_of(is_non_null_unit("str")), description="array of non-null strings"),
        ArgumentSpec(expected=STR, accepts=is_exact(STR), description="separator"),
    ),
    result_type=_result,
)


__all__ = ["JOIN"]
