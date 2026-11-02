"""Lower the ``expand`` expression operator."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..sql import SqlNode

from ....expressions.ir import OperationExpressionIR
from ...protocols import LoweringContext, Operand


@dataclass(frozen=True, slots=True)
class Expand:
    operator = "expand"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        from ....relational.interfaces import expansion_scope

        return context.expansion(expansion_scope(expression))


__all__ = ["Expand"]
