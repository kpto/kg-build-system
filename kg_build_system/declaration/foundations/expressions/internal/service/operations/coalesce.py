"""The null-replacing coalesce operation."""
from __future__ import annotations

from ...._private.operations import coalesce_validate
from .......kernel.internal.types import non_nullable
from .spec import ArgumentSpec, OperationSpec


COALESCE = OperationSpec(
    name="coalesce",
    arity=(2, None),
    arguments=(ArgumentSpec(description="value or fallback"),),
    repeat_last_argument=True,
    result_type=lambda types, parameters: non_nullable(types[0]),
    validate_arguments=coalesce_validate,
)


__all__ = ["COALESCE"]
