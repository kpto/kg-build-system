"""Structural expression traversal.

Only the four expression DTO node kinds are tested here. Every operator is looked up in the
registry, so this function never grows a new branch when an operator is added.
"""
from __future__ import annotations

from sqlglot import exp

from .sql import SqlNode

from kg_build_system.distribution.languages.expressions.model.internal import ExpressionDTO, FieldReferenceDTO, LiteralExpressionDTO, OperationExpressionDTO, VariableExpressionDTO
from .context import DuckDbExpressionContext
from .literals import literal_sql
from .sql import identifier


def _field(
    expression: FieldReferenceDTO, context: DuckDbExpressionContext,
) -> SqlNode:
    result: SqlNode = exp.column(
        expression.field.field,
        table=context.alias_for(expression.field.relation),
        quoted=True,
    )
    for part in expression.path:
        result = exp.Dot(this=result, expression=identifier(part))
    return result


def _variable(
    expression: VariableExpressionDTO, context: DuckDbExpressionContext,
) -> SqlNode:
    value = context.variables.get(expression.name)
    if value is None:
        raise ValueError(f"unbound expression variable {expression.name!r}")
    return value.copy()


def _operation(
    expression: OperationExpressionDTO, context: DuckDbExpressionContext,
) -> SqlNode:
    name = expression.operator.name
    emitter = context.operators.get(name)
    if emitter is None:
        raise ValueError(
            f"DuckDB does not support expression operator {name!r}"
        )
    operands = tuple(context.operand(argument) for argument in expression.arguments)
    return emitter.emit(expression, operands, context)


def emit_expression(
    expression: ExpressionDTO, context: DuckDbExpressionContext,
) -> SqlNode:
    if isinstance(expression, LiteralExpressionDTO):
        return literal_sql(expression)
    if isinstance(expression, VariableExpressionDTO):
        return _variable(expression, context)
    if isinstance(expression, FieldReferenceDTO):
        return _field(expression, context)
    if isinstance(expression, OperationExpressionDTO):
        return _operation(expression, context)
    raise TypeError(f"unsupported expression node {expression!r}")


__all__ = ["emit_expression"]
