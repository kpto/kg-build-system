"""DuckDB lowering: expression trees, relation plans and row-source plans.

The only dispatch here is a registry lookup. An operator is one implementation
in :mod:`.operators`; a row-source node is one implementation in
:mod:`.row_sources`. Adding either does not edit this module.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace

from sqlglot import exp

from .nodes import SqlNode

from ....expressions.ir import ExpressionIR
from ....relational.ir import FilterIR, RelationPlanIR
from ....table.interfaces import ShapeField
from ....table.ir import RowSourcePlanIR
from ...protocols import ExpressionLowerer, RowSourceLowerer
from .context import DuckDBLoweringContext
from .operators import DEFAULT_OPERATORS, compose_operators
from .row_sources import DEFAULT_ROW_SOURCES, compose_row_sources
from .sql import identifier, present_filter


def _identity(value: SqlNode) -> SqlNode:
    return value


_FILTER_MODES: Mapping[str, Callable[[SqlNode], SqlNode]] = {
    "present": present_filter,
    "true": _identity,
}


@dataclass(frozen=True, slots=True)
class DuckDBLowering:
    """The complete set of DuckDB lowerers."""

    operators: Mapping[str, ExpressionLowerer[SqlNode]] = field(
        default_factory=lambda: DEFAULT_OPERATORS,
    )
    row_sources: Mapping[type, RowSourceLowerer[SqlNode]] = field(
        default_factory=lambda: DEFAULT_ROW_SOURCES,
    )

    def with_operators(
        self, *lowerers: ExpressionLowerer[SqlNode],
    ) -> "DuckDBLowering":
        return replace(
            self,
            operators=compose_operators(self.operators.values(), lowerers),
        )

    def with_row_sources(
        self, *lowerers: RowSourceLowerer[SqlNode],
    ) -> "DuckDBLowering":
        return replace(
            self,
            row_sources=compose_row_sources(self.row_sources.values(), lowerers),
        )


DEFAULT_LOWERING = DuckDBLowering()


def lower_expression(
    expression: ExpressionIR,
    *,
    aliases: Mapping[str, str] | None = None,
    expansions: Mapping[tuple[str, ...], SqlNode] | None = None,
    lowering: DuckDBLowering = DEFAULT_LOWERING,
) -> SqlNode:
    """Lower one expression with no surrounding relation plan."""
    context = DuckDBLoweringContext(
        lowering.operators,
        aliases=aliases or {},
        expansions=expansions or {},
    )
    return context.lower(expression)


def lower_expression_sql(
    expression: ExpressionIR,
    *,
    aliases: Mapping[str, str] | None = None,
    lowering: DuckDBLowering = DEFAULT_LOWERING,
) -> str:
    return lower_expression(
        expression, aliases=aliases, lowering=lowering,
    ).sql(dialect="duckdb")


def lower_relation_sql(
    plan: RelationPlanIR, *, lowering: DuckDBLowering = DEFAULT_LOWERING,
) -> str:
    """Render a self-contained relation plan into DuckDB SQL."""
    if not plan.scans:
        query = exp.select(exp.Literal.number(1)).subquery("constant_input")
        select = exp.select("*").from_(query)
    else:
        first, *remaining = plan.scans
        select = exp.select("*").from_(
            exp.Table(
                this=identifier(first.relation),
                alias=exp.TableAlias(this=identifier(first.alias, quoted=False)),
            )
        )
        for scan in remaining:
            select = select.join(
                exp.Table(
                    this=identifier(scan.relation),
                    alias=exp.TableAlias(
                        this=identifier(scan.alias, quoted=False),
                    ),
                ),
                join_type="CROSS",
            )
    context = DuckDBLoweringContext(
        lowering.operators,
        aliases={scan.source: scan.alias for scan in plan.scans},
    )
    for expansion in plan.expands:
        value = context.lower(expansion.expression)
        select = select.join(
            exp.Unnest(
                expressions=[value],
                alias=exp.TableAlias(
                    this=identifier(expansion.alias, quoted=False),
                    columns=[identifier("item", quoted=False)],
                ),
            ),
            join_type="CROSS",
        )
        context = context.with_expansion(
            expansion.scope,
            exp.Dot(
                this=identifier(expansion.alias, quoted=False),
                expression=identifier("item"),
            ),
        )
    if plan.filters:
        predicate = None
        for item in plan.filters:
            current = _filter(item, context)
            predicate = current if predicate is None else exp.And(
                this=predicate, expression=current,
            )
        select = select.where(predicate)
    return select.select(*(
        exp.alias_(context.lower(expression), name, quoted=True)
        for name, expression in plan.outputs
    ), append=False).sql(dialect="duckdb")


def _filter(item: FilterIR, context: DuckDBLoweringContext) -> SqlNode:
    try:
        render = _FILTER_MODES[item.mode]
    except KeyError as error:
        raise ValueError(f"unknown filter mode {item.mode!r}") from error
    return render(context.lower(item.expression))


def lower_row_source_sql(
    plan: RowSourcePlanIR,
    relations: Mapping[str, str],
    shapes: Mapping[str, tuple[ShapeField, ...]],
    *,
    lowering: DuckDBLowering = DEFAULT_LOWERING,
) -> str:
    """Render one row-source plan as DuckDB SQL over already-named relations."""
    from .row_sources.context import PlanContext

    lowerer = lowering.row_sources.get(type(plan))
    if lowerer is None:
        raise TypeError(f"unsupported row-source plan {plan!r}")
    context = PlanContext(relations, shapes, lowering.operators)
    return lowerer.lower(plan, context)


__all__ = [
    "DEFAULT_LOWERING",
    "DuckDBLowering",
    "lower_expression",
    "lower_expression_sql",
    "lower_relation_sql",
    "lower_row_source_sql",
]
