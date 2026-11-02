"""The Boolean disjunction operation."""
from __future__ import annotations

from ....types.internal import BOOL, NullableType
from ._predicates import is_unit
from .spec import ArgumentSpec, OperationSpec


def _result(types, parameters):
    return NullableType(BOOL) if any(isinstance(item, NullableType) for item in types) else BOOL


OR = OperationSpec(
    name="or",
    arity=2,
    arguments=(
        ArgumentSpec(accepts=is_unit("bool"), description="Boolean value"),
        ArgumentSpec(accepts=is_unit("bool"), description="Boolean value"),
    ),
    result_type=_result,
)


__all__ = ["OR"]
