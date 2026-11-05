"""Construct literal selections and portable expression values.

Example:
    ```python
    from kg_build_system import value_expression

    assert value_expression(1).logical_type.name == "int"
    ```
"""
from __future__ import annotations

from typing import Any, overload

from kg_build_system.kernel.model.public.types import LogicalType
from ...model.public.selection import Selection
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
def value_expression(
    value: Any, *, logical_type: LogicalType | None = None,
) -> Selection[Any]: ...


def value_expression(
    value: Any, *, logical_type: LogicalType | None = None,
) -> Selection[Any]:
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
    value: Any, *, logical_type: LogicalType | None = None,
) -> Any:
    """Build canonical literal data, inferring the type when unambiguous.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.service.public import literal
        from kg_build_system import INT

        assert literal(1, logical_type=INT).logical_type == INT
        ```
    """
    return literal_impl(value, logical_type=logical_type)


__all__ = ["literal", "value_expression"]
