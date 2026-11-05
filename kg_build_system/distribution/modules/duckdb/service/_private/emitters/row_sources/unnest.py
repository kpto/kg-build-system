"""Row-source unnest emitter."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlglot import exp

from kg_build_system.distribution.languages.data.model.internal.dto import (
    RowUnnestDTO,
)

from ..sql import identifier, relation_table

if TYPE_CHECKING:
    from ..protocols import RowSourceEmissionContext


class UnnestEmitter:
    """Expand one array field into rows, preserving every other field."""

    node_type = RowUnnestDTO

    def emit(self, plan: RowUnnestDTO, context: RowSourceEmissionContext) -> str:
        input_key = context.source_key(plan.input)
        alias = "_kg_src"
        value = context.emit_expression(plan.expression, {input_key: alias})
        fields = exp.Star(except_=exp.Tuple(expressions=[
            exp.column(plan.field, quoted=True),
        ]))
        select = exp.select(
            fields,
            exp.alias_(
                exp.Anonymous(this="unnest", expressions=[value]),
                plan.field,
                quoted=True,
            ),
        ).from_(relation_table(context.relation_for(plan.input), alias))
        return select.sql(dialect="duckdb")


__all__ = ["UnnestEmitter"]
