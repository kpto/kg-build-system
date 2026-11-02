"""Lower the ``where_present`` expression operator."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..sql import SqlNode

from ....expressions.ir import OperationExpressionIR
from ...protocols import LoweringContext, Operand
from .base import require_arity


@dataclass(frozen=True, slots=True)
class WherePresent:
    operator = "where_present"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        require_arity(
            expression, operands, 1, "where_present requires one argument",
        )
        return operands[0].sql()


__all__ = ["WherePresent"]
