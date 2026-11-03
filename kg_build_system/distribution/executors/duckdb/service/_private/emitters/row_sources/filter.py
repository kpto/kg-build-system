"""Row-filter emitter, including expansions used by the predicate."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlglot import exp

from ..sql import SqlNode

from kg_build_system.distribution.languages.expressions.service.internal import walk_expression_dto
from kg_build_system.distribution.languages.expressions.model.internal import OperationExpressionDTO
from ..planning import expansion_scope
from kg_build_system.distribution.languages.table.model.internal.dto import RowFilterDTO

if TYPE_CHECKING:
    from ..protocols import RowSourceEmissionContext
from .context import PlanContext
from ..context import DuckDbExpressionContext
from ..sql import identifier, relation_table


def _with_expansions(
    select: SqlNode,
    predicate: object,
    context: PlanContext,
    aliases: dict[str, str],
) -> tuple[SqlNode, DuckDbExpressionContext]:
    local = context.expression_context(aliases)
    for operation in walk_expression_dto(predicate):  # type: ignore[arg-type]
        if not isinstance(operation, OperationExpressionDTO):
            continue
        if operation.operator != "expand":
            continue
        scope = expansion_scope(operation)
        if scope in local.expansions:
            continue
        value = local.emit(operation.arguments[0])
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


class FilterEmitter:
    node_type = RowFilterDTO

    def emit(self, plan: RowFilterDTO, context: PlanContext) -> str:
        input_key = context.source_key(plan.input)
        alias = "_kg_src"
        select = exp.select("*").from_(
            relation_table(context.relation_for(plan.input), alias)
        )
        expanded, local = _with_expansions(
            select, plan.predicate, context, {input_key: alias},
        )
        return expanded.where(local.emit(plan.predicate)).sql(dialect="duckdb")


__all__ = ["FilterEmitter"]
