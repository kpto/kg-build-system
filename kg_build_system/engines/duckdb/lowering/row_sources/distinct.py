"""Row-distinct lowering."""
from __future__ import annotations

from sqlglot import exp

from .....table.ir import RowDistinctIR
from ....protocols import RowSourceContext
from ..sql import identifier


class DistinctLowerer:
    node_type = RowDistinctIR

    def lower(self, plan: RowDistinctIR, context: RowSourceContext) -> str:
        return (
            exp.select("*")
            .distinct()
            .from_(exp.Table(this=identifier(context.relation_for(plan.input))))
            .sql(dialect="duckdb")
        )


__all__ = ["DistinctLowerer"]
