"""Lower the ``sort`` expression operator."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..sql import SqlNode

from ....expressions.ir import OperationExpressionIR
from ...protocols import LoweringContext, Operand
from .base import require_arity


@dataclass(frozen=True, slots=True)
class Sort:
    operator = "sort"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        require_arity(expression, operands, 1, "sort requires one argument")
        return exp.Anonymous(this="list_sort", expressions=[operands[0].sql()])


__all__ = ["Sort"]
