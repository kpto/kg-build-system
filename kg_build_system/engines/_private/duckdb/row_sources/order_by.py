"""Row-order lowering."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlglot import exp

from .....table.internal.ir import RowOrderByIR

if TYPE_CHECKING:
    from ....internal.protocols import RowSourceContext
from ..sql import relation_table


class OrderByLowerer:
    node_type = RowOrderByIR

    def lower(self, plan: RowOrderByIR, context: RowSourceContext) -> str:
        source_key = context.source_key(plan.input)
        alias = "_kg_src"
        select = exp.select("*").from_(
            relation_table(context.relation_for(plan.input), alias)
        )
        return select.order_by(*(
            exp.Ordered(
                this=context.lower_expression(key.expression, {source_key: alias}),
                desc=not key.ascending,
            )
            for key in plan.keys
        )).sql(dialect="duckdb")


__all__ = ["OrderByLowerer"]
