"""Lower the ``concat`` expression operator."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..sql import SqlNode

from ....expressions.ir import OperationExpressionIR
from ...protocols import LoweringContext, Operand


@dataclass(frozen=True, slots=True)
class Concat:
    operator = "concat"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        return exp.Anonymous(
            this="concat", expressions=[operand.sql() for operand in operands],
        )


__all__ = ["Concat"]
