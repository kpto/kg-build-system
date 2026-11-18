"""A project relation operation: one global count over any row source."""

from __future__ import annotations

from collections.abc import Sequence

from kg_build_system import (
    RelationOperation,
    RelationOperationSpec,
    Selection,
    Shape,
)
from kg_build_system.distribution.languages.data.model.internal.dto import (
    RowOperationDTO,
)
from kg_build_system.distribution.modules.duckdb import (
    RowSourceEmissionContext,
)


class CountRow(Shape):
    count: Selection[int]


COUNT_ROWS = RelationOperationSpec(
    name="count_rows",
    output=CountRow,
    grain="one_total",
)
count_rows = RelationOperation(COUNT_ROWS)


class CountRowsEmitter:
    """Emit one row with the input row count."""

    node_type = RowOperationDTO

    def emit(
        self,
        plan: RowOperationDTO,
        context: RowSourceEmissionContext,
    ) -> str:
        relation = context.relation_for(plan.input)
        return f"SELECT COUNT(*) AS count FROM {relation}"


__all__ = [
    "COUNT_ROWS",
    "CountRow",
    "CountRowsEmitter",
    "count_rows",
]
