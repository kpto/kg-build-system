"""The row-preserving array item transformation operation."""
from __future__ import annotations

from ..._private.operations import (
    transform_items_result, transform_items_validate,
)
from ..._private.predicates import is_array
from .spec import ArgumentSpec, OperationSpec, ParameterSpec


TRANSFORM_ITEMS = OperationSpec(
    name="transform_items",
    arity=2,
    arguments=(
        ArgumentSpec(accepts=is_array, description="array value"),
        ArgumentSpec(description="item expression"),
    ),
    parameters=(ParameterSpec("item", default="item", accepts=lambda value: isinstance(value, str) and bool(value)),),
    result_type=transform_items_result,
    validate_arguments=transform_items_validate,
)


__all__ = ["TRANSFORM_ITEMS"]
