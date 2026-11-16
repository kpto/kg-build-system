"""Construct literal selections and portable expression values.

Example:
    ```python
    from kg_build_system import value_expression

    assert value_expression(1).logical_type.name == "int"
    ```
"""
from __future__ import annotations

from typing import overload

from kg_build_system.kernel.model.public.types import (
    Array, Date, LogicalType, Time, Timestamp, Uuid,
)
from ...model.public.selection import Selection
from ...model.public.values import LiteralValue, ValueExpression
from ..internal.construction import literal as literal_impl
from ..internal.construction import value_expression as value_expression_impl
from ..internal.selections import select_expression as select_expression_impl


@overload
def value_expression(value: bool, *, logical_type: None = None) -> Selection[bool]: ...
@overload
def value_expression(value: int, *, logical_type: None = None) -> Selection[int]: ...
@overload
def value_expression(value: float, *, logical_type: None = None) -> Selection[float]: ...
@overload
def value_expression(value: str, *, logical_type: None = None) -> Selection[str]: ...
@overload
def value_expression(value: Date, *, logical_type: None = None) -> Selection[Date]: ...
@overload
def value_expression(value: Time, *, logical_type: None = None) -> Selection[Time]: ...
@overload
def value_expression(
    value: Timestamp, *, logical_type: None = None,
) -> Selection[Timestamp]: ...
@overload
def value_expression(value: Uuid, *, logical_type: None = None) -> Selection[Uuid]: ...
@overload
def value_expression[T: LiteralValue](
    value: list[T], *, logical_type: None = None,
) -> Selection[Array[T]]: ...
@overload
def value_expression(
    value: None, *, logical_type: LogicalType,
) -> Selection[None]: ...
@overload
def value_expression(
    value: LiteralValue, *, logical_type: LogicalType | None = None,
) -> Selection[object]: ...


def value_expression(
    value: LiteralValue, *, logical_type: LogicalType | None = None,
) -> Selection[object]:
    """Construct the selection for a portable literal.

    ``value`` is a canonical scalar or a homogeneous array of them. The logical
    type is inferred when it is unambiguous; pass ``logical_type`` for a null,
    an empty array or an array whose item type is not inferable.

    Example:
        ```python
        from kg_build_system import value_expression

        assert value_expression(1).logical_type.name == "int"
        ```
    """
    return select_expression_impl(
        value_expression_impl(value, logical_type=logical_type)
    )


def literal(
    value: LiteralValue, *, logical_type: LogicalType | None = None,
) -> ValueExpression[object]:
    """Build canonical literal data, inferring the type when unambiguous.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.service.public import literal
        from kg_build_system import INT

        assert literal(1, logical_type=INT).logical_type == INT
        ```
    """
    return ValueExpression(literal_impl(value, logical_type=logical_type))


__all__ = ["literal", "value_expression"]
