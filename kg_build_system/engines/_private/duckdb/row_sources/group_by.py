"""Row-group-by lowering."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlglot import exp

from .....table.internal.ir import RowGroupByIR

if TYPE_CHECKING:
    from ....internal.protocols import RowSourceContext
from ..sql import identifier, present_filter, relation_table, struct_pack


class GroupByLowerer:
    node_type = RowGroupByIR

    def lower(self, plan: RowGroupByIR, context: RowSourceContext) -> str:
        key = context.source_key(plan.input)
        alias = "_kg_src"
        rendered = tuple(
            (name, context.lower_expression(expression, {key: alias}))
            for name, expression in plan.keys
        )
        key_columns = tuple(f"_kg_key_{index}" for index in range(len(rendered)))
        member = struct_pack(context.shape_for(plan.input), alias)
        select = exp.select(
            *[
                exp.alias_(expression, column, quoted=True)
                for (_, expression), column in zip(rendered, key_columns)
            ],
            exp.alias_(member, "_kg_member", quoted=True),
        ).from_(relation_table(context.relation_for(plan.input), alias))
        predicate = None
        for _, expression in rendered:
            present = present_filter(expression)
            predicate = present if predicate is None else exp.And(
                this=predicate, expression=present,
            )
        select = select.where(predicate)
        grouped = exp.select(
            exp.alias_(
                exp.Anonymous(
                    this="struct_pack",
                    expressions=[
                        exp.PropertyEQ(
                            this=identifier(name),
                            expression=exp.column(column, quoted=True),
                        )
                        for (name, _), column in zip(rendered, key_columns)
                    ],
                ),
                "by",
                quoted=True,
            ),
            exp.alias_(
                exp.Anonymous(
                    this="list",
                    expressions=[exp.column("_kg_member", quoted=True)],
                ),
                "members",
                quoted=True,
            ),
        ).from_(select.subquery("_kg_group_keys", copy=False)).group_by(*[
            exp.column(column, quoted=True) for column in key_columns
        ])
        return grouped.sql(dialect="duckdb")


__all__ = ["GroupByLowerer"]
