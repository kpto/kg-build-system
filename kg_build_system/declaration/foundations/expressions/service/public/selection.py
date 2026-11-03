"""Selection construction, struct navigation and authoring normalization."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..internal.selections import as_expression as as_expression_impl
from ..internal.selections import select_expression as select_expression_impl
from ..internal.selections import select_member as select_member_impl

if TYPE_CHECKING:
    from kg_build_system.kernel.model.public.types import LogicalType, StructType
    from ...model.public.selections.value import ValueInput, ValueSelection
    from ...model.public.values import ValueExpression


def select_expression[T](expression: ValueExpression[T]) -> ValueSelection[T]:
    """Wrap a bindable expression in the selection matching its logical shape.

    Example:
        ```python
        from kg_build_system import ValueSelection, value_expression
        from kg_build_system.declaration.foundations.expressions.service.public import select_expression

        assert isinstance(select_expression(value_expression(1)), ValueSelection)
        ```
    """
    return select_expression_impl(expression)


def select_member(
    name: str, logical_type: LogicalType, declaration: StructType,
) -> ValueSelection[Any]:
    """Create the temporary selection returned by a field on a struct proxy.

    Example:
        ```python
        from kg_build_system.declaration.foundations.expressions.service.public import select_member
        from kg_build_system import STR
        from kg_build_system.kernel.model.public.types import StructType

        declaration = StructType("models", "Site")
        member = select_member("name", STR, declaration)
        assert member.logical_type == STR
        ```
    """
    return select_member_impl(name, logical_type, declaration)


def as_expression[T](value: ValueInput[T]) -> ValueExpression[T]:
    """Normalize a terminal authoring input to its bindable expression.

    Example:
        ```python
        from kg_build_system import as_expression, value_expression

        expression = value_expression("site::")
        assert as_expression(expression) is expression
        ```
    """
    return as_expression_impl(value)


__all__ = ["as_expression", "select_expression", "select_member"]
