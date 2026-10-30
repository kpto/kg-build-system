"""Small helpers shared by expression lowerers."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..nodes import SqlNode

from .....expressions.ir import OperationExpressionIR
from ....protocols import LoweringContext, Operand


def require_arity(
    expression: OperationExpressionIR,
    operands: Sequence[Operand[SqlNode]],
    expected: int,
    message: str,
) -> None:
    if len(operands) != expected:
        raise ValueError(message)


@dataclass(frozen=True, slots=True)
class BinaryLowerer:
    """An operator that renders two operands through one SQL constructor."""

    operator: str
    build: Callable[[SqlNode, SqlNode], SqlNode]
    message: str

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        require_arity(expression, operands, 2, self.message)
        return self.build(operands[0].sql(), operands[1].sql())


__all__ = ["BinaryLowerer", "require_arity"]
