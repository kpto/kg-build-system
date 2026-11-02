"""Lower the ``drop_null_items`` expression operator."""
from __future__ import annotations

from typing import TYPE_CHECKING

from collections.abc import Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..sql import SqlNode

from .....expressions.internal.ir import OperationExpressionIR

if TYPE_CHECKING:
    from ....internal.protocols import LoweringContext, Operand
from .base import require_arity


@dataclass(frozen=True, slots=True)
class DropNullItems:
    operator = "drop_null_items"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        require_arity(
            expression, operands, 1, "drop_null_items requires one argument",
        )
        item = exp.column("_kg_item", quoted=False)
        return exp.Anonymous(
            this="list_filter",
            expressions=[
                operands[0].sql(),
                exp.Lambda(
                    this=exp.Not(this=exp.Is(
                        this=item.copy(), expression=exp.null(),
                    )),
                    expressions=[item],
                ),
            ],
        )


__all__ = ["DropNullItems"]
