"""Array item transformations behind the authoring array family."""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from kg_build_system.kernel.model.public.types import ArrayType, NullableType, StructType
from ...model.internal.model import VariableExpression
from .apply import apply_operation
from .semantics import row_effects

if TYPE_CHECKING:
    from ...model.public.values import ValueExpression


def _transform_items(
    expression: ValueExpression[Any],
    selector: Callable[[Any], ValueExpression[Any]],
) -> ValueExpression[Any]:
    """Apply one typed selector to every element of an array."""
    from .factory import wrap_expression
    from .selections import as_expression, select_expression
    from .visitors import walk_expression

    logical_type = expression.logical_type
    array_nullable = isinstance(logical_type, NullableType)
    array_base = logical_type.value if array_nullable else logical_type
    if not isinstance(array_base, ArrayType):
        raise TypeError("transform_items requires an array expression")
    element = array_base.item
    element_nullable = isinstance(element, NullableType)
    element_base = element.value if element_nullable else element

    item_expression = wrap_expression(
        VariableExpression(name="item", logical_type=element_base)
    )
    proxy = (
        select_expression(item_expression)
        if isinstance(element_base, StructType)
        else item_expression
    )
    body = as_expression(selector(proxy))
    if any(row_effects(node.row_semantics) for node in walk_expression(body.model)):
        raise TypeError("transform_items selectors must not contain row effects")

    return apply_operation(
        "transform_items",
        expression.model,
        body.model,
        item="item",
    )


def _drop_null_items(expression: ValueExpression[Any]) -> ValueExpression[Any]:
    """Drop null items while keeping the array itself present or absent."""
    logical_type = expression.logical_type
    array_base = (
        logical_type.value if isinstance(logical_type, NullableType) else logical_type
    )
    if not isinstance(array_base, ArrayType):
        raise TypeError("drop_null_items requires an array expression")
    if not isinstance(array_base.item, NullableType):
        return expression
    return apply_operation("drop_null_items", expression.model)


def _array_operation(
    expression: ValueExpression[Any], operator: str,
) -> ValueExpression[Any]:
    """Apply a null-preserving array operator."""
    return apply_operation(operator, expression.model)


__all__: list[str] = []
