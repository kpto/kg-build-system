"""Small helpers shared by expression lowerers."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..sql import SqlNode

from ....expressions.ir import OperationExpressionIR
from ...protocols import LoweringContext, Operand


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


def _split(text: SqlNode, separator: SqlNode) -> SqlNode:
    return exp.Anonymous(
        this="string_split",
        expressions=[text.copy(), separator.copy()],
    )


def _separator_parameters(
    expression: OperationExpressionIR,
    operands: Sequence[Operand[SqlNode]],
    context: LoweringContext[SqlNode],
) -> tuple[SqlNode, SqlNode, int, bool]:
    require_arity(
        expression, operands, 2, f"{expression.operator} requires two arguments",
    )
    occurrence = context.parameter(expression, "occurrence")
    include_separator = context.parameter(expression, "include_separator")
    if not isinstance(occurrence, int) or occurrence < 1:
        raise ValueError(
            f"{expression.operator} occurrence must be a positive integer"
        )
    if not isinstance(include_separator, bool):
        raise ValueError(
            f"{expression.operator} include_separator must be a Boolean"
        )
    return operands[0].sql(), operands[1].sql(), occurrence, include_separator


__all__ = ["BinaryLowerer", "require_arity"]
