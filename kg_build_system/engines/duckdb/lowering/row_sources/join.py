"""Row-join lowering."""
from __future__ import annotations

from sqlglot import exp

from .....table.ir import RowJoinIR
from ....protocols import RowSourceContext
from ..sql import identifier, nullable_struct


_JOIN_TYPES = {
    "inner": "INNER",
    "left": "LEFT",
    "right": "RIGHT",
    "full": "FULL",
}


class JoinLowerer:
    node_type = RowJoinIR

    def lower(self, plan: RowJoinIR, context: RowSourceContext) -> str:
        left_key = context.source_key(plan.left)
        right_key = context.source_key(plan.right)
        left_alias, right_alias = "_kg_left", "_kg_right"
        left_expression = context.lower_expression(
            plan.left_key, {left_key: left_alias},
        )
        right_expression = context.lower_expression(
            plan.right_key, {right_key: right_alias},
        )
        left_relation = exp.select(
            "*", exp.alias_(exp.true(), "_kg_present", quoted=True),
        ).from_(
            exp.Table(this=identifier(context.relation_for(plan.left))),
        ).subquery(left_alias, copy=False)
        right_relation = exp.select(
            "*", exp.alias_(exp.true(), "_kg_present", quoted=True),
        ).from_(
            exp.Table(this=identifier(context.relation_for(plan.right))),
        ).subquery(right_alias, copy=False)
        select = exp.select(
            exp.alias_(
                exp.Coalesce(
                    this=left_expression,
                    expressions=[right_expression],
                ),
                "on",
                quoted=True,
            ),
            exp.alias_(
                nullable_struct(
                    context.shape_for(plan.left), left_alias,
                    nullable=plan.how in {"right", "full"},
                ),
                "left",
                quoted=True,
            ),
            exp.alias_(
                nullable_struct(
                    context.shape_for(plan.right), right_alias,
                    nullable=plan.how in {"left", "full"},
                ),
                "right",
                quoted=True,
            ),
        ).from_(left_relation)
        return select.join(
            right_relation,
            on=exp.EQ(this=left_expression, expression=right_expression),
            join_type=_JOIN_TYPES[plan.how],
        ).sql(dialect="duckdb")


__all__ = ["JoinLowerer"]
