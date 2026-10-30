"""Structural expression traversal.

Only the four IR node kinds are tested here. Every operator is looked up in the
registry, so this function never grows a new branch when an operator is added.
"""
from __future__ import annotations

from sqlglot import exp

from .nodes import SqlNode

from ....expressions.ir import (
    ExpressionIR,
    FieldReferenceExpressionIR,
    LiteralExpressionIR,
    OperationExpressionIR,
    VariableExpressionIR,
)
from .context import DuckDBLoweringContext
from .literals import lower_literal
from .sql import identifier


def _field(
    expression: FieldReferenceExpressionIR, context: DuckDBLoweringContext,
) -> SqlNode:
    result: SqlNode = exp.column(
        expression.path[0], table=context.alias_for(expression.source), quoted=True,
    )
    for part in expression.path[1:]:
        result = exp.Dot(this=result, expression=identifier(part))
    return result


def _variable(
    expression: VariableExpressionIR, context: DuckDBLoweringContext,
) -> SqlNode:
    value = context.variables.get(expression.name)
    if value is None:
        raise ValueError(f"unbound expression variable {expression.name!r}")
    return value.copy()


def _operation(
    expression: OperationExpressionIR, context: DuckDBLoweringContext,
) -> SqlNode:
    lowerer = context.operators.get(expression.operator)
    if lowerer is None:
        raise ValueError(
            f"DuckDB does not support expression operator {expression.operator!r}"
        )
    operands = tuple(context.operand(argument) for argument in expression.arguments)
    return lowerer.lower(expression, operands, context)


def lower_expression(
    expression: ExpressionIR, context: DuckDBLoweringContext,
) -> SqlNode:
    if isinstance(expression, LiteralExpressionIR):
        return lower_literal(expression)
    if isinstance(expression, VariableExpressionIR):
        return _variable(expression, context)
    if isinstance(expression, FieldReferenceExpressionIR):
        return _field(expression, context)
    if isinstance(expression, OperationExpressionIR):
        return _operation(expression, context)
    raise TypeError(f"unsupported expression node {expression!r}")


__all__ = ["lower_expression"]
