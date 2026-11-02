"""The array operation that removes null items."""
from __future__ import annotations

from ...types.interfaces import ArrayType, NullableType, non_nullable
from ._predicates import is_array
from .spec import ArgumentSpec, OperationSpec


def _result(types, parameters):
    source = types[0]
    array = non_nullable(source)
    assert isinstance(array, ArrayType)
    item = array.item.value if isinstance(array.item, NullableType) else array.item
    result = ArrayType(item)
    if isinstance(source, NullableType):
        result = NullableType(result)
    return result


DROP_NULL_ITEMS = OperationSpec(
    name="drop_null_items",
    arity=1,
    arguments=(ArgumentSpec(accepts=is_array, description="array value"),),
    result_type=_result,
)


__all__ = ["DROP_NULL_ITEMS"]
