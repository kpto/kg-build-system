"""Construct typed authoring expressions and portable literals.

Example:
    ```python
    from kg_build_system import value_expression
    from kg_build_system.expressions import literal
    from kg_build_system.types import INT

    assert value_expression(1).logical_type.name == "int"
    assert literal(1, logical_type=INT).logical_type == INT
    ```
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, overload

from ...types.internal import LogicalType
from .._private.factory import value_expression as _value_expression
from .._private.factory import wrap_expression as _wrap_expression
from .._private.literals import literal as _literal
from ..internal.model import ExpressionNode, LiteralExpression
from .values import ValueExpression

if TYPE_CHECKING:
    from .boolean import BoolExpression
    from .numeric import FloatExpression, IntExpression
    from .text import StrExpression


def wrap_expression(expression: ExpressionNode) -> ValueExpression[Any]:
    """Wrap canonical data in the most specific runtime authoring family.

    Example:
        ```python
        from kg_build_system import BoolExpression, value_expression
        from kg_build_system.expressions import wrap_expression

        wrapped = wrap_expression(value_expression(True).model)
        assert isinstance(wrapped, BoolExpression)
        ```
    """
    return _wrap_expression(expression)


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
    return _value_expression(value, logical_type=logical_type)


def literal(
    value: Any, *, logical_type: LogicalType | None = None,
) -> LiteralExpression:
    """Build canonical literal data, inferring the type when unambiguous.

    ``value`` must match the representative Python class of the resolved unit;
    a null or an empty array needs an explicit ``logical_type``.

    Example:
        ```python
        from kg_build_system.expressions import literal
        from kg_build_system.types import INT

        assert literal(1, logical_type=INT).logical_type == INT
        ```
    """
    return _literal(value, logical_type=logical_type)


__all__ = ["literal", "value_expression", "wrap_expression"]
