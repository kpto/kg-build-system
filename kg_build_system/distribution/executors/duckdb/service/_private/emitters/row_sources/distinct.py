"""Row-distinct emitter."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlglot import exp

from kg_build_system.distribution.languages.data.model.internal.dto import RowDistinctDTO

if TYPE_CHECKING:
    from ..protocols import RowSourceEmissionContext
from ..sql import identifier


class DistinctEmitter:
    node_type = RowDistinctDTO

    def emit(self, plan: RowDistinctDTO, context: RowSourceEmissionContext) -> str:
        return (
            exp.select("*")
            .distinct()
            .from_(exp.Table(this=identifier(context.relation_for(plan.input))))
            .sql(dialect="duckdb")
        )


__all__ = ["DistinctEmitter"]
