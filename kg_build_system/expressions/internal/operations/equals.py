"""The text equality operation."""
from __future__ import annotations

from ....types.internal import BOOL, STR, NullableType, non_nullable
from ._predicates import is_unit
from .spec import ArgumentSpec, OperationSpec


def _result(types, parameters):
    return NullableType(BOOL) if any(isinstance(item, NullableType) for item in types) else BOOL


def _validate(arguments, parameters) -> None:
    if any(non_nullable(argument.logical_type) != STR for argument in arguments):
        raise TypeError("equals requires str arguments")


EQUALS = OperationSpec(
    name="equals",
    arity=2,
    arguments=(
        ArgumentSpec(accepts=is_unit("str"), description="str value"),
        ArgumentSpec(accepts=is_unit("str"), description="str value"),
    ),
    result_type=_result,
    validate_arguments=_validate,
)


__all__ = ["EQUALS"]
