"""Selection construction, struct navigation and authoring normalization.

The selection classes live in their family modules. This module exposes the
normalizers and family-choosing rules implemented in ``_private.selections``;
the private module uses late imports so the family modules stay independent of
each other.

Example:
    ```python
    from kg_build_system import ValueSelection, value_expression
    from kg_build_system.expressions.selections import select_expression

    assert isinstance(select_expression(value_expression(1)), ValueSelection)
    ```
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..._private.selections import _expand, _pick
from ..._private.selections import as_expression as _as_expression
from ..._private.selections import select_expression as _select_expression
from ..._private.selections import (
    select_expression_from_node as _select_expression_from_node,
)
from ..._private.selections import select_member as _select_member

if TYPE_CHECKING:
    from ....types.internal import LogicalType, StructType
    from ..values import ValueExpression
    from .value import ValueInput, ValueSelection


def select_expression_from_node(expression):
    return _select_expression_from_node(expression)


def select_expression[T](expression: ValueExpression[T]) -> ValueSelection[T]:
    """Wrap a bindable expression in the selection matching its logical shape.

    Example:
        ```python
        from kg_build_system import ValueSelection, value_expression
        from kg_build_system.expressions import select_expression

        assert isinstance(select_expression(value_expression(1)), ValueSelection)
        ```
    """
    return _select_expression(expression)


def select_member(
    name: str, logical_type: LogicalType, declaration: StructType,
) -> ValueSelection[Any]:
    """Create the temporary selection returned by a field on a struct proxy.

    Example:
        ```python
        from kg_build_system.expressions import select_member
        from kg_build_system.types import STR
        from kg_build_system.types.internal import StructType

        declaration = StructType("models", "Site")
        member = select_member("name", STR, declaration)
        assert member.logical_type == STR
        ```
    """
    return _select_member(name, logical_type, declaration)


def as_expression[T](value: ValueInput[T]) -> ValueExpression[T]:
    """Normalize a terminal authoring input to its bindable expression.

    Example:
        ```python
        from kg_build_system import as_expression, value_expression

        expression = value_expression("site::")
        assert as_expression(expression) is expression
        ```
    """
    return _as_expression(value)


__all__ = [
    "as_expression", "select_expression", "select_expression_from_node",
    "select_member",
]
