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
from .types import CANONICAL_SQL_TYPES, ArraySqlType, SqlType, canonical_sql_type


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


def _typed_null_sql_type(logical_type: LogicalTypeIR) -> str | None:
    """The SQL a null literal carries, so a typed null stays its property's type.

    A bare ``NULL`` column materializes as an integer; a category slot an
    authoring binding leaves unbound lowers to a null of the slot's own type,
    which keeps the component's Parquet columns faithful to its declared
    schema. Structs cannot be property types, so only units and arrays compose.
    """
    value = logical_type.value if isinstance(logical_type, NullableTypeIR) else logical_type
    if isinstance(value, UnitTypeIR):
        return CANONICAL_SQL_TYPES.get(value.name)
    if isinstance(value, ArrayTypeIR):
        item = _typed_null_sql_type(value.item)
        return f"{item}[]" if item is not None else None
    return None


def _literal(expression: LiteralExpression) -> Any:
    value = _thaw(expression.value)
    if value is None:
        sql_type = _typed_null_sql_type(expression.logical_type)
        if sql_type is None:
            return exp.convert(value)
        return exp.cast(exp.null(), exp.DataType.build(sql_type))
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
    if expression.operator == "where_present" or expression.operator == "keep_if":
        # Both pass their value through; the row effect already became a plan filter.
        return _render(expression.arguments[0], context)
    arguments = tuple(_render(argument, context) for argument in expression.arguments)
    if expression.operator == "add":
        return exp.Add(this=arguments[0], expression=arguments[1])
    if expression.operator == "subtract":
        return exp.Sub(this=arguments[0], expression=arguments[1])
    if expression.operator == "equals":
        return exp.EQ(this=arguments[0], expression=arguments[1])
    if expression.operator == "concat":
        return exp.Anonymous(this="concat", expressions=list(arguments))
    if expression.operator == "replaced":
        return exp.Anonymous(this="replace", expressions=list(arguments))
    if expression.operator == "split_before":
        # LIST_EXTRACT(STRING_SPLIT(...), 1): the segment before the first
        # separator, and the whole string when the separator is absent.
        return exp.Anonymous(
            this="list_extract",
            expressions=[
                exp.Anonymous(
                    this="string_split",
                    expressions=[arguments[0], arguments[1].copy()],
                ),
                exp.Literal.number(1),
            ],
        )
    if expression.operator == "split_after":
        # Re-join the segments past the first separator, so later separators
        # stay part of the payload rather than being cut away.
        return exp.Anonymous(
            this="array_to_string",
            expressions=[
                exp.Anonymous(
                    this="list_slice",
                    expressions=[
                        exp.Anonymous(
                            this="string_split",
                            expressions=[arguments[0], arguments[1].copy()],
                        ),
                        exp.Literal.number(2),
                        exp.Literal.number(-1),
                    ],
                ),
                arguments[1].copy(),
            ],
        )
    if expression.operator == "text":
        return exp.Cast(this=arguments[0], to=exp.DataType.build("VARCHAR"))
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
    if expression.operator == "without_nulls":
        # LIST_FILTER keeps a null array null and drops only null items.
        item = exp.column("_kg_item")
        return exp.Anonymous(
            this="list_filter",
            expressions=[
                arguments[0],
                exp.Lambda(
                    this=exp.Not(this=exp.Is(this=item.copy(), expression=exp.null())),
                    expressions=[item],
                ),
            ],
        )
    if expression.operator == "map_items":
        # LIST_TRANSFORM maps each element to one member; a null list stays null.
        item = exp.column("_kg_item")
        member = _identifier(str(_parameter(expression, "name")))
        return exp.Anonymous(
            this="list_transform",
            expressions=[
                arguments[0],
                exp.Lambda(
                    this=exp.Dot(this=item.copy(), expression=member),
                    expressions=[item],
                ),
            ],
        )
    if expression.operator == "sorted":
        # LIST_SORT keeps a null array null and sorts the present items.
        return exp.Anonymous(this="list_sort", expressions=[arguments[0]])
    if expression.operator == "distinct":
        # LIST_DISTINCT keeps a null array null and keeps one copy per item.
        return exp.Anonymous(this="list_distinct", expressions=[arguments[0]])
    if expression.operator == "join":
        # ARRAY_TO_STRING keeps a null array null; items are non-null by type.
        return exp.Anonymous(
            this="array_to_string", expressions=[arguments[0], arguments[1]]
        )
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
            rendered = _render(item.expression, context)
            if item.mode == "true":
                current = rendered
            else:
                current = exp.Not(this=exp.Is(this=rendered, expression=exp.Null()))
            predicate = current if predicate is None else exp.And(this=predicate, expression=current)
        select = select.where(predicate)
    return select.select(*(
        exp.alias_(_render(expression, context), name, quoted=True)
        for name, expression in plan.outputs
    ), append=False).sql(dialect="duckdb")


__all__ = ["lower_relation_sql"]
