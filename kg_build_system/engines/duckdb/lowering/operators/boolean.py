"""Boolean expression operators."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..nodes import SqlNode

from .....expressions.ir import OperationExpressionIR
from ....protocols import LoweringContext, Operand
from .base import BinaryLowerer, require_arity

EQUALS = BinaryLowerer(
    "equals",
    lambda left, right: exp.EQ(this=left, expression=right),
    "equals requires two arguments",
)
AND = BinaryLowerer(
    "and",
    lambda left, right: exp.And(this=left, expression=right),
    "and requires two arguments",
)
OR = BinaryLowerer(
    "or",
    lambda left, right: exp.Or(this=left, expression=right),
    "or requires two arguments",
)

@dataclass(frozen=True, slots=True)
class Not:
    operator = "not"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        require_arity(expression, operands, 1, "not requires one argument")
        return exp.Not(this=operands[0].sql())


OPERATORS = (EQUALS, AND, OR, Not())

__all__ = ["OPERATORS"]
