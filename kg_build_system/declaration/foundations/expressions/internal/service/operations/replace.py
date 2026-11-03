"""The text replacement operation."""
from __future__ import annotations

from .......kernel.internal.types import STR, NullableType, non_nullable
from ._predicates import is_unit
from .spec import ArgumentSpec, OperationSpec


def _result(types, parameters):
    return NullableType(STR) if any(isinstance(item, NullableType) for item in types) else STR


def _validate(arguments, parameters) -> None:
    if any(non_nullable(argument.logical_type) != STR for argument in arguments):
        raise TypeError("replace requires str arguments")


REPLACE = OperationSpec(
    name="replace",
    arity=3,
    arguments=(
        ArgumentSpec(accepts=is_unit("str"), description="str value"),
        ArgumentSpec(accepts=is_unit("str"), description="str value"),
        ArgumentSpec(accepts=is_unit("str"), description="str value"),
    ),
    result_type=_result,
    validate_arguments=_validate,
)


__all__ = ["REPLACE"]
