"""The text concatenation operation."""
from __future__ import annotations

from .......kernel.internal.types import STR, NullableType, non_nullable
from ._predicates import is_unit
from .spec import ArgumentSpec, OperationSpec


def _result(types, parameters):
    return NullableType(STR) if any(isinstance(item, NullableType) for item in types) else STR


def _validate(arguments, parameters) -> None:
    if any(non_nullable(argument.logical_type) != STR for argument in arguments):
        raise TypeError("concat requires str arguments")


CONCAT = OperationSpec(
    name="concat",
    arity=(2, None),
    arguments=(ArgumentSpec(accepts=is_unit("str"), description="str value"),),
    repeat_last_argument=True,
    result_type=_result,
    validate_arguments=_validate,
)


__all__ = ["CONCAT"]
