"""Row-filter lowering."""
from __future__ import annotations

from sqlglot import exp

from .....table.ir import RowFilterIR
from ....protocols import RowSourceContext
from ..sql import relation_table


class FilterLowerer:
    node_type = RowFilterIR

    def lower(self, plan: RowFilterIR, context: RowSourceContext) -> str:
        key = context.source_key(plan.input)
        alias = "_kg_src"
        predicate = context.lower_expression(plan.predicate, {key: alias})
        return (
            exp.select("*")
            .from_(relation_table(context.relation_for(plan.input), alias))
            .where(predicate)
            .sql(dialect="duckdb")
        )


__all__ = ["FilterLowerer"]
