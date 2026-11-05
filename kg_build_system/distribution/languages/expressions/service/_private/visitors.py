"""Traversal and immutable rewriting for canonical expression trees."""
from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, TypeVar

from ...model.internal.model import (
    Expression, ExpressionNode, FieldReferenceExpression, LiteralExpression,
    LookupExpression, OperationExpression, VariableExpression,
)
from .build import with_arguments

if TYPE_CHECKING:
    from ..internal.visitors import ExpressionVisitor

T_co = TypeVar("T_co", covariant=True)


def visit_expression(
    expression: Expression, visitor: ExpressionVisitor[T_co],
) -> T_co:
    """Dispatch one expression node to its visitor method."""
    if isinstance(expression, LiteralExpression):
        return visitor.visit_literal(expression)
    if isinstance(expression, FieldReferenceExpression):
        return visitor.visit_field_reference(expression)
    if isinstance(expression, LookupExpression):
        return visitor.visit_lookup(expression)
    if isinstance(expression, OperationExpression):
        return visitor.visit_operation(expression)
    if isinstance(expression, VariableExpression):
        return visitor.visit_variable(expression)
    raise TypeError(f"unknown expression node {expression!r}")


def walk_expression(expression: ExpressionNode) -> Iterator[ExpressionNode]:
    """Yield an expression tree in deterministic pre-order."""
    yield expression
    if isinstance(expression, LookupExpression):
        yield from walk_expression(expression.key)
    if isinstance(expression, OperationExpression):
        for argument in expression.arguments:
            yield from walk_expression(argument)


def rewrite_expression(
    expression: ExpressionNode,
    transform: Callable[[ExpressionNode], ExpressionNode],
) -> ExpressionNode:
    """Rewrite children first, preserving unchanged operation identities."""
    current = expression
    if isinstance(expression, LookupExpression):
        key = rewrite_expression(expression.key, transform)
        if key != expression.key:
            import dataclasses

            current = dataclasses.replace(expression, key=key)
    if isinstance(expression, OperationExpression):
        arguments = tuple(
            rewrite_expression(argument, transform)
            for argument in expression.arguments
        )
        current = with_arguments(expression, arguments)
    return transform(current)


__all__ = ["rewrite_expression", "visit_expression", "walk_expression"]
