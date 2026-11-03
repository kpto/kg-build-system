"""Row-order emitter."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlglot import exp

from kg_build_system.declaration.languages.table.model.internal.dto import RowOrderByDTO

if TYPE_CHECKING:
    from ..protocols import RowSourceEmissionContext
from ..sql import relation_table


class OrderByEmitter:
    node_type = RowOrderByDTO

    def emit(self, plan: RowOrderByDTO, context: RowSourceEmissionContext) -> str:
        source_key = context.source_key(plan.input)
        alias = "_kg_src"
        select = exp.select("*").from_(
            relation_table(context.relation_for(plan.input), alias)
        )
        return select.order_by(*(
            exp.Ordered(
                this=context.emit_expression(expression, {source_key: alias}),
                desc=not ascending,
            )
            for expression, ascending in plan.keys
        )).sql(dialect="duckdb")


__all__ = ["OrderByEmitter"]
