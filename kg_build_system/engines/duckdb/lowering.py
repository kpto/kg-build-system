"""Render logical relational plans as inspectable DuckDB SQL."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlglot import exp

from ...expressions import (
    FieldReferenceExpression, LiteralExpression, OperationExpression,
)
from ...expressions.ir import FrozenObject
from ...relational import RelationPlan


def _identifier(value: str, *, quoted: bool = True) -> exp.Identifier:
    return exp.Identifier(this=value, quoted=quoted)


def _thaw(value: Any) -> Any:
    if isinstance(value, FrozenObject):
        return {key: _thaw(item) for key, item in value.items}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _parameter(expression: OperationExpression, name: str) -> Any:
    for parameter in expression.parameters:
        if parameter.name == name:
            return _thaw(parameter.value)
    raise ValueError(f"{expression.operator} requires parameter {name!r}")


@dataclass(slots=True)
class _Context:
    aliases: dict[str, str]
    expansions: dict[tuple[str, ...], Any]


def _field(expression: FieldReferenceExpression, context: _Context) -> Any:
    alias = context.aliases.get(expression.source)
    if alias is None:
        raise ValueError(f"no scan alias for logical source {expression.source!r}")
    result: Any = exp.column(expression.path[0], table=alias, quoted=True)
    for part in expression.path[1:]:
        result = exp.Dot(this=result, expression=_identifier(part))
    return result


def _render(expression, context: _Context) -> Any:
    if isinstance(expression, LiteralExpression):
        return exp.convert(_thaw(expression.value))
    if isinstance(expression, FieldReferenceExpression):
        return _field(expression, context)
    if not isinstance(expression, OperationExpression):
        raise TypeError(f"unsupported expression node {expression!r}")
    if expression.operator == "each":
        scope = expression.row_semantics.effects[-1].scope
        try:
            return context.expansions[scope]
        except KeyError as error:
            raise ValueError(f"expansion scope {scope!r} was not planned") from error
    if expression.operator == "when_present":
        return _render(expression.arguments[0], context)
    arguments = tuple(_render(argument, context) for argument in expression.arguments)
    if expression.operator == "add":
        return exp.Add(this=arguments[0], expression=arguments[1])
    if expression.operator == "subtract":
        return exp.Sub(this=arguments[0], expression=arguments[1])
    if expression.operator == "concat":
        return exp.Anonymous(this="concat", expressions=list(arguments))
    if expression.operator == "coalesce":
        return exp.Coalesce(this=arguments[0], expressions=list(arguments[1:]))
    if expression.operator == "not":
        return exp.Not(this=arguments[0])
    if expression.operator == "and":
        return exp.And(this=arguments[0], expression=arguments[1])
    if expression.operator == "or":
        return exp.Or(this=arguments[0], expression=arguments[1])
    if expression.operator == "struct_field":
        return exp.Dot(this=arguments[0], expression=_identifier(str(_parameter(expression, "name"))))
    raise ValueError(f"DuckDB does not support expression operator {expression.operator!r}")


def lower_relation_sql(plan: RelationPlan) -> str:
    """Render a self-contained relation plan into DuckDB SQL."""
    if not plan.scans:
        query = exp.select(exp.Literal.number(1)).subquery("constant_input")
        select = exp.select("*").from_(query)
    else:
        first, *remaining = plan.scans
        select = exp.select("*").from_(
            exp.Table(this=_identifier(first.relation), alias=exp.TableAlias(this=_identifier(first.alias, quoted=False)))
        )
        for scan in remaining:
            select = select.join(
                exp.Table(this=_identifier(scan.relation), alias=exp.TableAlias(this=_identifier(scan.alias, quoted=False))),
                join_type="CROSS",
            )
    context = _Context(
        {scan.source: scan.alias for scan in plan.scans},
        {},
    )
    for expansion in plan.expands:
        value = _render(expansion.expression, context)
        select = select.join(
            exp.Unnest(
                expressions=[value],
                alias=exp.TableAlias(
                    this=_identifier(expansion.alias, quoted=False),
                    columns=[_identifier("item", quoted=False)],
                ),
            ),
            join_type="CROSS",
        )
        context.expansions[expansion.scope] = exp.Dot(
            this=_identifier(expansion.alias, quoted=False),
            expression=_identifier("item"),
        )
    if plan.filters:
        predicate = None
        for item in plan.filters:
            current = exp.Not(
                this=exp.Is(this=_render(item.expression, context), expression=exp.Null())
            )
            predicate = current if predicate is None else exp.And(this=predicate, expression=current)
        select = select.where(predicate)
    return select.select(*(
        exp.alias_(_render(expression, context), name, quoted=True)
        for name, expression in plan.outputs
    ), append=False).sql(dialect="duckdb")


__all__ = ["lower_relation_sql"]
