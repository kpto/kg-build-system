"""The row-preserving array item transformation operation."""
from __future__ import annotations

from ...._private.semantics import row_effects
from .......kernel.internal.types import ArrayType, NullableType, non_nullable
from ._predicates import is_array
from .spec import ArgumentSpec, OperationSpec, ParameterSpec


def _validate(arguments, parameters) -> None:
    body = arguments[1]
    if any(row_effects(node.row_semantics) for node in _walk(body)):
        raise TypeError("transform_items selectors must not contain row effects")


def _walk(node):
    yield node
    for argument in getattr(node, "arguments", ()):
        yield from _walk(argument)


def _result(types, parameters):
    source, body = types
    array = non_nullable(source)
    assert isinstance(array, ArrayType)
    item = array.item
    if isinstance(item, NullableType) and not isinstance(body, NullableType):
        body = NullableType(body)
    result = ArrayType(body)
    if isinstance(source, NullableType):
        result = NullableType(result)
    return result


TRANSFORM_ITEMS = OperationSpec(
    name="transform_items",
    arity=2,
    arguments=(
        ArgumentSpec(accepts=is_array, description="array value"),
        ArgumentSpec(description="item expression"),
    ),
    parameters=(ParameterSpec("item", default="item", accepts=lambda value: isinstance(value, str) and bool(value)),),
    result_type=_result,
    validate_arguments=_validate,
)


__all__ = ["TRANSFORM_ITEMS"]
