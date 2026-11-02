"""Lower the ``expand`` expression operator."""
from __future__ import annotations

from typing import TYPE_CHECKING

from collections.abc import Sequence
from dataclasses import dataclass

from ..sql import SqlNode

from .....expressions.internal.ir import OperationExpressionIR

if TYPE_CHECKING:
    from ....internal.protocols import LoweringContext, Operand


@dataclass(frozen=True, slots=True)
class Expand:
    operator = "expand"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        from .....relational.internal import expansion_scope

        return context.expansion(expansion_scope(expression))


__all__ = ["Expand"]
