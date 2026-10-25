"""Render logical relational plans as inspectable DuckDB SQL."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlglot import exp

from ...expressions.ir import (
    FieldReferenceExpressionIR as FieldReferenceExpression,
    LiteralExpressionIR as LiteralExpression,
    OperationExpressionIR as OperationExpression,
)
from ..._frozen_json import FrozenObject
from ...relational.ir import RelationPlanIR as RelationPlan
from ...relational.planner import expansion_scope
from ...types import TEXT_CANONICAL_UNIT_NAMES
from ...types.ir import ArrayTypeIR, LogicalTypeIR, NullableTypeIR, UnitTypeIR
from .types import ArraySqlType, SqlType, canonical_sql_type


def _identifier(value: str, *, quoted: bool = True) -> exp.Identifier:
    return exp.Identifier(this=value, quoted=quoted)


def _thaw(value: Any) -> Any:
    if isinstance(value, FrozenObject):
        return {key: _thaw(item) for key, item in value.items}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


# A literal of one of these units is frozen as canonical text, which alone would lower
# to a VARCHAR; the node's logical type names the unit, so it lowers to a typed literal.
def _text_unit_sql_type(logical_type: LogicalTypeIR) -> SqlType | None:
    """The canonical type a literal frozen as text carries, as the SQL algebra accepts it.

    Only the node's logical type distinguishes that text from a `str`, and an array names
    its SQL type one item at a time, so `Array[Date]` reaches DuckDB as `DATE[]`. A logical
    type built only of bool, int, float and str freezes as JSON that lowers to the SQL type
    of its own accord, and answers None so it is left exactly as it froze.
    """
    value = logical_type.value if isinstance(logical_type, NullableTypeIR) else logical_type
    if isinstance(value, UnitTypeIR):
        return value.name if value.name in TEXT_CANONICAL_UNIT_NAMES else None
    if isinstance(value, ArrayTypeIR):
        item = _text_unit_sql_type(value.item)
        return ArraySqlType(item=item) if item is not None else None
    return None


def _literal(expression: LiteralExpression) -> Any:
    value = _thaw(expression.value)
    canonical = _text_unit_sql_type(expression.logical_type)
    if canonical is not None and isinstance(value, (str, list)):
        # An array cast applies element-wise and is checked, so the items stay plain text
        # literals and one outer cast names the type of the whole frozen value.
        return exp.cast(
            exp.convert(value),
            exp.DataType.build(canonical_sql_type(canonical)),
        )
    return exp.convert(value)


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
        return _literal(expression)
    if isinstance(expression, FieldReferenceExpression):
        return _field(expression, context)
    if not isinstance(expression, OperationExpression):
        raise TypeError(f"unsupported expression node {expression!r}")
    if expression.operator == "expand":
        scope = expansion_scope(expression)
        try:
            return context.expansions[scope]
        except KeyError as error:
            raise ValueError(f"expansion scope {scope!r} was not planned") from error
    if expression.operator == "where_present":
        return _render(expression.arguments[0], context)
    arguments = tuple(_render(argument, context) for argument in expression.arguments)
    if expression.operator == "add":
        return exp.Add(this=arguments[0], expression=arguments[1])
    if expression.operator == "subtract":
        return exp.Sub(this=arguments[0], expression=arguments[1])
    if expression.operator == "concat":
        return exp.Anonymous(this="concat", expressions=list(arguments))
    if expression.operator == "equals":
        return exp.EQ(this=arguments[0], expression=arguments[1])
    if expression.operator == "replace":
        return exp.Anonymous(this="replace", expressions=list(arguments))
    if expression.operator == "to_string":
        if not arguments:
            raise ValueError("to_string requires one argument")
        source_type = expression.arguments[0].logical_type
        base = (
            source_type.value
            if isinstance(source_type, NullableTypeIR) else source_type
        )
        rendered = exp.Cast(
            this=arguments[0], to=exp.DataType.build("VARCHAR"),
        )
        if isinstance(base, UnitTypeIR) and base.name == "timestamp":
            return exp.Anonymous(
                this="replace",
                expressions=[
                    rendered,
                    exp.Literal.string(" "),
                    exp.Literal.string("T"),
                ],
            )
        return rendered
    if expression.operator in {"before_separator", "after_separator"}:
        if len(arguments) != 2:
            raise ValueError(f"{expression.operator} requires two arguments")
        side = (
            "before" if expression.operator == "before_separator" else "after"
        )
        occurrence = _parameter(expression, "occurrence")
        include_separator = _parameter(expression, "include_separator")
        if not isinstance(occurrence, int) or occurrence < 1:
            raise ValueError(
                f"{expression.operator} occurrence must be a positive integer"
            )
        if not isinstance(include_separator, bool):
            raise ValueError(
                f"{expression.operator} include_separator must be a Boolean"
            )

        def split() -> Any:
            return exp.Anonymous(
                this="string_split",
                expressions=[arguments[0].copy(), arguments[1].copy()],
            )

        sliced = exp.Anonymous(
            this="list_slice",
            expressions=[
                split(),
                exp.Literal.number(1 if side == "before" else occurrence + 1),
                exp.Literal.number(occurrence if side == "before" else -1),
            ],
        )
        base = exp.Anonymous(
            this="array_to_string",
            expressions=[sliced, arguments[1].copy()],
        )
        if not include_separator:
            return base
        present = exp.GT(
            this=exp.Anonymous(this="len", expressions=[split()]),
            expression=exp.Literal.number(occurrence),
        )
        separator = arguments[1].copy()
        if side == "before":
            suffix = exp.Case(
                ifs=[exp.If(this=present, true=separator)],
                default=exp.Literal.string(""),
            )
            return exp.Anonymous(
                this="concat", expressions=[base, suffix],
            )
        joined = exp.Anonymous(
            this="concat", expressions=[separator, base],
        )
        return exp.Case(
            ifs=[exp.If(this=present, true=joined)],
            default=exp.Literal.string(""),
        )
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
