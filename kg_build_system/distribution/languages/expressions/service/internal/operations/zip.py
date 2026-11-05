"""The value-level array pairing operation."""
from __future__ import annotations

from ..._private.operations import zip_result
from ..._private.predicates import is_array
from .spec import ArgumentSpec, OperationSpec


ZIP = OperationSpec(
    name="zip",
    arity=2,
    arguments=(
        ArgumentSpec(accepts=is_array, description="left array value"),
        ArgumentSpec(accepts=is_array, description="right array value"),
    ),
    result_type=zip_result,
)


__all__ = ["ZIP"]
