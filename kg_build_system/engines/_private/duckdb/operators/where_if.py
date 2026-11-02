"""Lower the ``where_if`` expression operator."""
from __future__ import annotations

from typing import TYPE_CHECKING

from collections.abc import Sequence
from dataclasses import dataclass

from ..sql import SqlNode

from .....expressions.internal.ir import OperationExpressionIR

if TYPE_CHECKING:
    from ....internal.protocols import LoweringContext, Operand
from .base import require_arity


@dataclass(frozen=True, slots=True)
class WhereIf:
    operator = "where_if"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        require_arity(expression, operands, 2, "where_if requires two arguments")
        return operands[0].sql()


__all__ = ["WhereIf"]
