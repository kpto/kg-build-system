"""Traversal and immutable rewriting for canonical expression trees."""
from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Protocol, TypeVar

from ...model.internal.model import (
    Expression, ExpressionNode, FieldReferenceExpression, LiteralExpression,
    LookupExpression, OperationExpression, VariableExpression,
)

T_co = TypeVar("T_co", covariant=True)


class ExpressionVisitor(Protocol[T_co]):
    def visit_literal(self, expression: LiteralExpression) -> T_co: ...
    def visit_field_reference(self, expression: FieldReferenceExpression) -> T_co: ...
    def visit_lookup(self, expression: LookupExpression) -> T_co: ...
    def visit_operation(self, expression: OperationExpression) -> T_co: ...
    def visit_variable(self, expression: VariableExpression) -> T_co: ...


def visit_expression(expression: Expression, visitor: ExpressionVisitor[T_co]) -> T_co:
    """Dispatch one expression node to its visitor method."""
    from .._private.visitors import visit_expression as visit

    return visit(expression, visitor)


def walk_expression(expression: ExpressionNode) -> Iterator[ExpressionNode]:
    """Yield an expression tree in deterministic pre-order."""
    from .._private.visitors import walk_expression as walk

    yield from walk(expression)


def rewrite_expression(
    expression: ExpressionNode,
    transform: Callable[[ExpressionNode], ExpressionNode],
) -> ExpressionNode:
    """Rewrite children first, preserving unchanged operation identities."""
    from .._private.visitors import rewrite_expression as rewrite

    return rewrite(expression, transform)


__all__ = ["ExpressionVisitor", "rewrite_expression", "visit_expression", "walk_expression"]
