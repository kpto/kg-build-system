"""The text-before-separator operation."""
from __future__ import annotations

from ....types.internal import STR, NullableType, non_nullable
from ._predicates import is_unit
from .spec import ArgumentSpec, OperationSpec, ParameterSpec


def _positive_integer(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _result(types, parameters):
    return NullableType(STR) if any(isinstance(item, NullableType) for item in types) else STR


def _validate(arguments, parameters) -> None:
    if any(non_nullable(argument.logical_type) != STR for argument in arguments):
        raise TypeError("before_separator requires str arguments")


BEFORE_SEPARATOR = OperationSpec(
    name="before_separator",
    arity=2,
    arguments=(
        ArgumentSpec(accepts=is_unit("str"), description="str value"),
        ArgumentSpec(accepts=is_unit("str"), description="separator"),
    ),
    parameters=(
        ParameterSpec("occurrence", default=1, accepts=_positive_integer),
        ParameterSpec("include_separator", default=False, accepts=lambda value: isinstance(value, bool)),
    ),
    result_type=_result,
    validate_arguments=_validate,
)


__all__ = ["BEFORE_SEPARATOR"]
