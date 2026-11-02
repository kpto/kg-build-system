"""Lower the ``coalesce`` expression operator."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..sql import SqlNode

from ....expressions.ir import OperationExpressionIR
from ...protocols import LoweringContext, Operand


@dataclass(frozen=True, slots=True)
class Coalesce:
    operator = "coalesce"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        if len(operands) < 2:
            raise ValueError("coalesce requires at least two arguments")
        return exp.Coalesce(
            this=operands[0].sql(),
            expressions=[operand.sql() for operand in operands[1:]],
        )


__all__ = ["Coalesce"]
