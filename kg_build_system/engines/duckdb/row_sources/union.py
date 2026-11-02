"""Row-union lowering."""
from __future__ import annotations

from sqlglot import exp

from ....table.ir import RowUnionIR
from ...protocols import RowSourceContext
from ..sql import identifier


class UnionLowerer:
    node_type = RowUnionIR

    def lower(self, plan: RowUnionIR, context: RowSourceContext) -> str:
        left = exp.select("*").from_(
            exp.Table(this=identifier(context.relation_for(plan.left)))
        )
        right = exp.select("*").from_(
            exp.Table(this=identifier(context.relation_for(plan.right)))
        )
        return exp.union(left, right, distinct=not plan.all).sql(dialect="duckdb")


__all__ = ["UnionLowerer"]
