"""Emit DuckDB SQL from engine-neutral expression and row-source plans.

Planning is done by the compilation relational package and produces no SQL. This
module is the only place where an expression tree or a plan becomes DuckDB SQL.
Dispatch is a registry lookup: an expression operator is one module in
:mod:`.operators`, a row-source node is one module in :mod:`.row_sources`, and
neither registry is edited to add an emitter.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from sqlglot import exp

from .context import DuckDbExpressionContext, LazyOperand
from .operators import DEFAULT_OPERATORS, compose_operators
from .protocols import ExpressionEmitter, RowSourceEmitter
from .row_sources import DEFAULT_ROW_SOURCES, compose_row_sources
from .row_sources.context import PlanContext
from .sql import SqlNode, identifier, present_filter

from kg_build_system.declaration.foundations.expressions.model.internal import ExpressionDTO
from .......pipeline.compile.model.internal import Filter, RelationPlan
from kg_build_system.declaration.languages.table.model.public import ShapeField
from kg_build_system.declaration.languages.table.model.internal.dto import RowSourcePlanDTO


def _identity(value: SqlNode) -> SqlNode:
    return value


_FILTER_MODES: Mapping[str, Callable[[SqlNode], SqlNode]] = {
    "present": present_filter,
    "true": _identity,
}


@dataclass(frozen=True, slots=True)
class DuckDbInstructionEmitter:
    """The complete set of DuckDB expression and row-source emitters."""

    operators: Mapping[str, ExpressionEmitter[SqlNode]] = field(
        default_factory=lambda: DEFAULT_OPERATORS,
    )
    row_sources: Mapping[type[Any], RowSourceEmitter[SqlNode]] = field(
        default_factory=lambda: DEFAULT_ROW_SOURCES,
    )

    def with_operators(
        self, *emitters: ExpressionEmitter[SqlNode],
    ) -> "DuckDbInstructionEmitter":
        return replace(
            self,
            operators=compose_operators(self.operators.values(), emitters),
        )

    def with_row_sources(
        self, *emitters: RowSourceEmitter[SqlNode],
    ) -> "DuckDbInstructionEmitter":
        return replace(
            self,
            row_sources=compose_row_sources(self.row_sources.values(), emitters),
        )

    def emit_expression(
        self,
        expression: ExpressionDTO,
        *,
        aliases: Mapping[str, str] | None = None,
        expansions: Mapping[tuple[str, ...], SqlNode] | None = None,
    ) -> SqlNode:
        """Emit one expression with no surrounding relation plan."""
        context = DuckDbExpressionContext(
            self.operators,
            aliases=aliases or {},
            expansions=expansions or {},
        )
        return context.emit(expression)

    def expression_sql(
        self,
        expression: ExpressionDTO,
        *,
        aliases: Mapping[str, str] | None = None,
    ) -> str:
        return self.emit_expression(
            expression, aliases=aliases,
        ).sql(dialect="duckdb")

    def relation_sql(self, plan: RelationPlan) -> str:
        """Render a self-contained relational product into DuckDB SQL."""
        if not plan.scans:
            query = exp.select(exp.Literal.number(1)).subquery("constant_input")
            select = exp.select("*").from_(query)
        else:
            first, *remaining = plan.scans
            select = exp.select("*").from_(
                exp.Table(
                    this=identifier(first.relation),
                    alias=exp.TableAlias(
                        this=identifier(first.alias, quoted=False),
                    ),
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
        context = DuckDbExpressionContext(
            self.operators,
            aliases={scan.source: scan.alias for scan in plan.scans},
        )
        for expansion in plan.expands:
            value = context.emit(expansion.expression)
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
            exp.alias_(context.emit(expression), name, quoted=True)
            for name, expression in plan.outputs
        ), append=False).sql(dialect="duckdb")

    def emit_row_source(
        self,
        plan: RowSourcePlanDTO,
        relations: Mapping[str, str],
        shapes: Mapping[str, tuple[ShapeField, ...]],
    ) -> str:
        """Render one row-source plan as DuckDB SQL over already-named relations."""
        emitter = self.row_sources.get(type(plan))
        if emitter is None:
            raise TypeError(f"unsupported row-source plan {plan!r}")
        context = PlanContext(relations, shapes, self.operators)
        return emitter.emit(plan, context)

    def row_source_sql(
        self,
        plan: RowSourcePlanDTO,
        relations: Mapping[str, str],
        shapes: Mapping[str, tuple[ShapeField, ...]],
    ) -> str:
        return self.emit_row_source(plan, relations, shapes)


def _filter(item: Filter, context: DuckDbExpressionContext) -> SqlNode:
    try:
        render = _FILTER_MODES[item.mode]
    except KeyError as error:
        raise ValueError(f"unknown filter mode {item.mode!r}") from error
    return render(context.emit(item.expression))


DEFAULT_EMITTER = DuckDbInstructionEmitter()


def emit_expression(
    expression: ExpressionDTO,
    *,
    aliases: Mapping[str, str] | None = None,
    expansions: Mapping[tuple[str, ...], SqlNode] | None = None,
    emitter: DuckDbInstructionEmitter = DEFAULT_EMITTER,
) -> SqlNode:
    """Emit one expression to a DuckDB SQL node without a relation plan."""
    return emitter.emit_expression(
        expression, aliases=aliases, expansions=expansions,
    )


def expression_sql(
    expression: ExpressionDTO,
    *,
    aliases: Mapping[str, str] | None = None,
    emitter: DuckDbInstructionEmitter = DEFAULT_EMITTER,
) -> str:
    """Render one expression directly as DuckDB SQL text."""
    return emitter.expression_sql(expression, aliases=aliases)


def relation_sql(
    plan: RelationPlan, *, emitter: DuckDbInstructionEmitter = DEFAULT_EMITTER,
) -> str:
    """Render a self-contained relational product as DuckDB SQL."""
    return emitter.relation_sql(plan)


def emit_row_source(
    plan: RowSourcePlanDTO,
    relations: Mapping[str, str],
    shapes: Mapping[str, tuple[ShapeField, ...]],
    *,
    emitter: DuckDbInstructionEmitter = DEFAULT_EMITTER,
) -> str:
    """Render one row-source plan as DuckDB SQL over already-named relations."""
    return emitter.emit_row_source(plan, relations, shapes)


def row_source_sql(
    plan: RowSourcePlanDTO,
    relations: Mapping[str, str],
    shapes: Mapping[str, tuple[ShapeField, ...]],
    *,
    emitter: DuckDbInstructionEmitter = DEFAULT_EMITTER,
) -> str:
    """Render one row-source plan as DuckDB SQL text."""
    return emitter.row_source_sql(plan, relations, shapes)


__all__ = [
    "DEFAULT_EMITTER",
    "DuckDbExpressionContext",
    "DuckDbInstructionEmitter",
    "LazyOperand",
    "emit_expression",
    "emit_row_source",
    "expression_sql",
    "relation_sql",
    "row_source_sql",
]
