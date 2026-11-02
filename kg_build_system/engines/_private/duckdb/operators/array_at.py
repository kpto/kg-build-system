"""Lower the ``array_at`` expression operator."""
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
class ArrayAt:
    operator = "array_at"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        require_arity(
            expression, operands, 2, "array_at requires an array and an index",
        )
        return exp.Anonymous(
            this="list_extract",
            expressions=[
                operands[0].sql(),
                exp.Add(
                    this=operands[1].sql(), expression=exp.Literal.number(1),
                ),
            ],
        )


__all__ = ["ArrayAt"]
