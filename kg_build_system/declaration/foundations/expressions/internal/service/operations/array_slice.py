"""The 0-based, end-exclusive array slice operation."""
from __future__ import annotations

from .......kernel.internal.types import INT
from ._predicates import is_array, is_exact
from .spec import ArgumentSpec, OperationSpec


ARRAY_SLICE = OperationSpec(
    name="array_slice",
    arity=3,
    arguments=(
        ArgumentSpec(accepts=is_array, description="array value"),
        ArgumentSpec(expected=INT, accepts=is_exact(INT), description="integer start"),
        ArgumentSpec(expected=INT, accepts=is_exact(INT), description="integer end"),
    ),
    result_type=lambda types, parameters: types[0],
)


__all__ = ["ARRAY_SLICE"]
