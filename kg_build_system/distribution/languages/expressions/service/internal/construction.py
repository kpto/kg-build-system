"""Expression construction interface used by the public service."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kg_build_system.kernel.model.public.types import LogicalType
from ...model.internal.model import LiteralExpression

if TYPE_CHECKING:
    from ...model.public.values import ValueExpression


def wrap_expression(expression: Any) -> ValueExpression[Any]:
    """Wrap canonical data in the most specific authoring family."""
    from .._private.factory import wrap_expression as wrap

    return wrap(expression)


def value_expression(
    value: Any, *, logical_type: LogicalType | None = None,
) -> ValueExpression[Any]:
    """Construct the most specific typed expression for a portable literal."""
    from .._private.factory import value_expression as build

    return build(value, logical_type=logical_type)


def literal(
    value: Any, *, logical_type: LogicalType | None = None,
) -> LiteralExpression:
    """Build canonical literal data, inferring the type when unambiguous."""
    from .._private.literals import literal as build

    return build(value, logical_type=logical_type)


__all__ = ["literal", "value_expression", "wrap_expression"]
