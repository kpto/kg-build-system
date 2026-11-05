"""Structural expression traversal.

Only the four expression DTO node kinds are tested here. Every operator is looked up in the
registry, so this function never grows a new branch when an operator is added.
"""
from __future__ import annotations

from sqlglot import exp

from .sql import SqlNode

from kg_build_system.distribution.languages.expressions.model.internal import (
    ExpressionDTO, FieldReferenceDTO, LiteralExpressionDTO,
    LookupExpressionDTO, OperationExpressionDTO, VariableExpressionDTO,
)
from .context import DuckDbExpressionContext
from .literals import literal_sql
from .sql import identifier, struct_pack


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


def _lookup(
    expression: LookupExpressionDTO, context: DuckDbExpressionContext,
) -> SqlNode:
    target = expression.relation.name
    relation = context.relations.get(target, target)
    fields = context.shapes.get(target)
    if not fields:
        raise ValueError(f"lookup target {target!r} has no planned shape")
    target_field = expression.target_field
    if not target_field and isinstance(expression.key, FieldReferenceDTO):
        target_field = expression.key.field.field
    if not target_field:
        raise ValueError("lookup requires a target key column")
    key = context.emit(expression.key)
    alias = "_kg_lookup"
    record = struct_pack(fields, alias)
    target_column = exp.column(
        target_field, table=alias, quoted=True,
    )
    query = exp.select(
        exp.Anonymous(this="list", expressions=[record]),
    ).from_(
        exp.Table(
            this=identifier(relation),
            alias=exp.TableAlias(this=identifier(alias, quoted=False)),
        ),
    ).where(exp.And(
        this=exp.EQ(this=target_column, expression=key.copy()),
        expression=exp.Not(this=exp.Is(
            this=key.copy(), expression=exp.Null(),
        )),
    ))
    return exp.Subquery(this=query)


def emit_expression(
    expression: ExpressionDTO, context: DuckDbExpressionContext,
) -> SqlNode:
    if isinstance(expression, LiteralExpressionDTO):
        return literal_sql(expression)
    if isinstance(expression, VariableExpressionDTO):
        return _variable(expression, context)
    if isinstance(expression, FieldReferenceDTO):
        return _field(expression, context)
    if isinstance(expression, LookupExpressionDTO):
        return _lookup(expression, context)
    if isinstance(expression, OperationExpressionDTO):
        return _operation(expression, context)
    raise TypeError(f"unsupported expression node {expression!r}")


__all__ = ["emit_expression"]
