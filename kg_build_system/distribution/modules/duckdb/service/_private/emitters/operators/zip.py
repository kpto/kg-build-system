"""Emit the value-level ``zip`` expression operator."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlglot import exp

from ..sql import SqlNode

from kg_build_system.distribution.languages.expressions.model.internal import (
    OperationExpressionDTO,
)

if TYPE_CHECKING:
    from ..protocols import EmissionContext, Operand
from .base import require_arity


def _item(item: SqlNode, index: int) -> SqlNode:
    return exp.Bracket(
        this=item.copy(), expressions=[exp.Literal.number(index)],
    )


@dataclass(frozen=True, slots=True)
class Zip:
    """Pair two arrays by position, refusing a length mismatch."""

    operator = "zip"

    def emit(
        self,
        expression: OperationExpressionDTO,
        operands: Sequence[Operand[SqlNode]],
        context: EmissionContext[SqlNode],
    ) -> SqlNode:
        del context
        require_arity(expression, operands, 2, "zip requires two arguments")
        left = operands[0].sql()
        right = operands[1].sql()
        item = exp.column("_kg_pair", quoted=False)
        pair = exp.Anonymous(
            this="struct_pack",
            expressions=[
                exp.PropertyEQ(
                    this=exp.to_identifier("left"), expression=_item(item, 0),
                ),
                exp.PropertyEQ(
                    this=exp.to_identifier("right"), expression=_item(item, 1),
                ),
            ],
        )
        paired = exp.Anonymous(
            this="list_transform",
            expressions=[
                exp.Anonymous(
                    this="list_zip",
                    expressions=[left.copy(), right.copy()],
                ),
                exp.Lambda(this=pair, expressions=[item.copy()]),
            ],
        )
        lengths_differ = exp.NEQ(
            this=exp.Anonymous(this="len", expressions=[left.copy()]),
            expression=exp.Anonymous(this="len", expressions=[right.copy()]),
        )
        absent = exp.Or(
            this=exp.Is(this=left.copy(), expression=exp.Null()),
            expression=exp.Is(this=right.copy(), expression=exp.Null()),
        )
        return exp.Case(
            ifs=[
                exp.If(this=absent, true=exp.Null()),
                exp.If(
                    this=lengths_differ,
                    true=exp.Anonymous(
                        this="error",
                        expressions=[
                            exp.Literal.string(
                                "zip arrays must have equal length"
                            ),
                        ],
                    ),
                ),
            ],
            default=paired,
        )


__all__ = ["Zip"]
