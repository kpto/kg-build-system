"""Emit the ``join`` expression operator."""
from __future__ import annotations

from typing import TYPE_CHECKING

from collections.abc import Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..sql import SqlNode

from .......declaration.foundations.expressions.internal import OperationExpressionDTO

if TYPE_CHECKING:
    from ..protocols import EmissionContext, Operand
from .base import require_arity


@dataclass(frozen=True, slots=True)
class ArrayJoin:
    operator = "join"

    def emit(
        self,
        expression: OperationExpressionDTO,
        operands: Sequence[Operand[SqlNode]],
        context: EmissionContext[SqlNode],
    ) -> SqlNode:
        require_arity(
            expression, operands, 2, "join requires an array and a separator",
        )
        return exp.Anonymous(
            this="array_to_string",
            expressions=[operands[0].sql(), operands[1].sql()],
        )


__all__ = ["ArrayJoin"]
