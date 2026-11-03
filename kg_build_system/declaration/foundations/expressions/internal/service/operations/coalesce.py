"""The null-replacing coalesce operation."""
from __future__ import annotations

from .......kernel.internal.types import NullableType, non_nullable
from .spec import ArgumentSpec, OperationSpec


def _validate(arguments, parameters) -> None:
    value = non_nullable(arguments[0].logical_type)
    for argument in arguments[1:]:
        if argument.logical_type != value:
            raise TypeError("coalesce arguments must share the value logical type")


COALESCE = OperationSpec(
    name="coalesce",
    arity=(2, None),
    arguments=(ArgumentSpec(description="value or fallback"),),
    repeat_last_argument=True,
    result_type=lambda types, parameters: non_nullable(types[0]),
    validate_arguments=_validate,
)


__all__ = ["COALESCE"]
