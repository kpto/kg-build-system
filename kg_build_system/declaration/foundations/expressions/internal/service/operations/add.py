"""The numeric addition operation."""
from __future__ import annotations

from .......kernel.internal.types import LogicalType
from ._predicates import is_numeric
from .spec import ArgumentSpec, OperationSpec


def _validate(arguments, parameters) -> None:
    left, right = (argument.logical_type for argument in arguments)
    if left != right:
        raise TypeError("add requires arguments of one numeric type")


ADD = OperationSpec(
    name="add",
    arity=2,
    arguments=(
        ArgumentSpec(accepts=is_numeric, description="numeric value"),
        ArgumentSpec(accepts=is_numeric, description="numeric value"),
    ),
    result_type=lambda types, parameters: types[0],
    validate_arguments=_validate,
)


__all__ = ["ADD"]
