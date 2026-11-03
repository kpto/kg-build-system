"""The array operation that removes null items."""
from __future__ import annotations

from ...._private.operations import drop_null_items_result
from ...._private.predicates import is_array
from .spec import ArgumentSpec, OperationSpec


DROP_NULL_ITEMS = OperationSpec(
    name="drop_null_items",
    arity=1,
    arguments=(ArgumentSpec(accepts=is_array, description="array value"),),
    result_type=drop_null_items_result,
)


__all__ = ["DROP_NULL_ITEMS"]
