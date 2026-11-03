"""Row-union emitter."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlglot import exp

from kg_build_system.declaration.languages.table.model.internal.dto import RowUnionDTO

if TYPE_CHECKING:
    from ..protocols import RowSourceEmissionContext
from ..sql import identifier


class UnionEmitter:
    node_type = RowUnionDTO

    def emit(self, plan: RowUnionDTO, context: RowSourceEmissionContext) -> str:
        left = exp.select("*").from_(
            exp.Table(this=identifier(context.relation_for(plan.left)))
        )
        right = exp.select("*").from_(
            exp.Table(this=identifier(context.relation_for(plan.right)))
        )
        return exp.union(left, right, distinct=not plan.all).sql(dialect="duckdb")


__all__ = ["UnionEmitter"]
