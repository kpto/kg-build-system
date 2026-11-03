"""Construct typed authoring expressions and portable literals.

Example:
    ```python
    from kg_build_system import value_expression
    from kg_build_system.declaration.foundations.expressions.service.public import literal
    from kg_build_system import INT

    assert value_expression(1).logical_type.name == "int"
    assert literal(1, logical_type=INT).logical_type == INT
    ```
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, overload

from kg_build_system.kernel.model.public.types import LogicalType
from ...model.internal.model import LiteralExpression
from ...model.public.values import ValueExpression
from ..internal.construction import literal as literal_impl
from ..internal.construction import value_expression as value_expression_impl
from ..internal.construction import wrap_expression as wrap_expression_impl

if TYPE_CHECKING:
    from ...model.public.boolean import BoolExpression
    from ...model.public.numeric import FloatExpression, IntExpression
    from ...model.public.text import StrExpression


def wrap_expression(expression: Any) -> ValueExpression[Any]:
    """Wrap canonical data in the most specific runtime authoring family.

    Example:
        ```python
        from kg_build_system import BoolExpression, value_expression
        from kg_build_system.declaration.foundations.expressions.service.public import wrap_expression

        wrapped = wrap_expression(value_expression(True).model)
        assert isinstance(wrapped, BoolExpression)
        ```
    """
    return wrap_expression_impl(expression)


@overload
def value_expression(value: bool, *, logical_type: None = None) -> "BoolExpression": ...
@overload
def value_expression(value: int, *, logical_type: None = None) -> "IntExpression": ...
@overload
def value_expression(value: float, *, logical_type: None = None) -> "FloatExpression": ...
@overload
def value_expression(value: str, *, logical_type: None = None) -> "StrExpression": ...
@overload
def value_expression(value: Any, *, logical_type: LogicalType | None = None) -> ValueExpression[Any]: ...


def value_expression(
    value: Any, *, logical_type: LogicalType | None = None,
) -> ValueExpression[Any]:
    """Construct the most specific typed expression for a portable literal.

    ``value`` is a canonical scalar or a homogeneous array of them. The logical
    type is inferred when it is unambiguous; pass ``logical_type`` for a null,
    an empty array or an array whose item type is not inferable.

    Example:
        ```python
        from kg_build_system import value_expression

        assert value_expression(1).logical_type.name == "int"
        ```
    """
    return value_expression_impl(value, logical_type=logical_type)


def literal(
    value: Any, *, logical_type: LogicalType | None = None,
) -> LiteralExpression:
    """Build canonical literal data, inferring the type when unambiguous.

    ``value`` must match the representative Python class of the resolved unit;
    a null or an empty array needs an explicit ``logical_type``.

    Example:
        ```python
        from kg_build_system.declaration.foundations.expressions.service.public import literal
        from kg_build_system import INT

        assert literal(1, logical_type=INT).logical_type == INT
        ```
    """
    return literal_impl(value, logical_type=logical_type)


__all__ = ["literal", "value_expression", "wrap_expression"]
