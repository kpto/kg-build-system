"""Framework-internal wrappers for relation planning.

The planning algorithms live in ``_private``; these wrappers keep the internal
service path stable for module compilers.
"""
from __future__ import annotations

from collections.abc import Mapping

from .....declaration.foundations.expressions.internal import (
    ExpressionDTO,
    OperationExpressionDTO,
)
from ..model import RelationPlan


def expansion_scope(expression: OperationExpressionDTO) -> tuple[str, ...]:
    """Derive a stable, plan-local identity for one explicit ``expand`` operation."""
    from ..._private import planning

    return planning.expansion_scope(expression)


def plan_product(
    outputs: Mapping[str, ExpressionDTO],
    relations: Mapping[str, str],
    *,
    predicates: tuple[ExpressionDTO, ...] = (),
) -> RelationPlan:
    """Plan one projection or binding without leaking its row effects elsewhere."""
    from ..._private import planning

    return planning.plan_product(outputs, relations, predicates=predicates)


__all__ = ["expansion_scope", "plan_product"]
