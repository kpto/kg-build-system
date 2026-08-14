"""Traversal and immutable rewriting for canonical expression trees."""
from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Protocol, TypeVar

from .models import Expression, ExpressionNode, FieldReferenceExpression, LiteralExpression, OperationExpression


T_co = TypeVar("T_co", covariant=True)


class ExpressionVisitor(Protocol[T_co]):
    def visit_literal(self, expression: LiteralExpression) -> T_co: ...
    def visit_field_reference(self, expression: FieldReferenceExpression) -> T_co: ...
    def visit_operation(self, expression: OperationExpression) -> T_co: ...


def visit_expression(expression: Expression, visitor: ExpressionVisitor[T_co]) -> T_co:
    if isinstance(expression, LiteralExpression):
        return visitor.visit_literal(expression)
    if isinstance(expression, FieldReferenceExpression):
        return visitor.visit_field_reference(expression)
    if isinstance(expression, OperationExpression):
        return visitor.visit_operation(expression)
    raise TypeError(f"unknown expression node {expression!r}")


def walk_expression(expression: ExpressionNode) -> Iterator[ExpressionNode]:
    """Yield an expression tree in deterministic pre-order."""
    yield expression
    if isinstance(expression, OperationExpression):
        for argument in expression.arguments:
            yield from walk_expression(argument)


def rewrite_expression(
    expression: ExpressionNode,
    transform: Callable[[ExpressionNode], ExpressionNode],
) -> ExpressionNode:
    """Rewrite children first, preserving unchanged operation identities."""
    current = expression
    if isinstance(expression, OperationExpression):
        arguments = tuple(rewrite_expression(argument, transform) for argument in expression.arguments)
        current = expression.with_arguments(arguments)
    return transform(current)


__all__ = ["ExpressionVisitor", "rewrite_expression", "visit_expression", "walk_expression"]
