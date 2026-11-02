"""Row-filter lowering, including expansions used by the predicate."""
from __future__ import annotations

from sqlglot import exp

from ..sql import SqlNode

from ....expressions.interfaces import walk_expression_ir
from ....expressions.ir import OperationExpressionIR
from ....relational.interfaces import expansion_scope
from ....table.ir import RowFilterIR
from ...protocols import RowSourceContext
from .context import PlanContext
from ..context import DuckDBLoweringContext
from ..sql import identifier, relation_table


def _with_expansions(
    select: SqlNode,
    predicate: object,
    context: PlanContext,
    aliases: dict[str, str],
) -> tuple[SqlNode, DuckDBLoweringContext]:
    local = context.expression_context(aliases)
    for operation in walk_expression_ir(predicate):  # type: ignore[arg-type]
        if not isinstance(operation, OperationExpressionIR):
            continue
        if operation.operator != "expand":
            continue
        scope = expansion_scope(operation)
        if scope in local.expansions:
            continue
        value = local.lower(operation.arguments[0])
        alias = f"expanded{len(local.expansions)}"
        select = select.join(
            exp.Unnest(
                expressions=[value],
                alias=exp.TableAlias(
                    this=identifier(alias, quoted=False),
                    columns=[identifier("item", quoted=False)],
                ),
            ),
            join_type="CROSS",
        )
        local = local.with_expansion(
            scope,
            exp.Dot(
                this=identifier(alias, quoted=False),
                expression=identifier("item"),
            ),
        )
    return select, local


class FilterLowerer:
    node_type = RowFilterIR

    def lower(self, plan: RowFilterIR, context: PlanContext) -> str:
        input_key = context.source_key(plan.input)
        alias = "_kg_src"
        select = exp.select("*").from_(
            relation_table(context.relation_for(plan.input), alias)
        )
        expanded, local = _with_expansions(
            select, plan.predicate, context, {input_key: alias},
        )
        return expanded.where(local.lower(plan.predicate)).sql(dialect="duckdb")


__all__ = ["FilterLowerer"]
