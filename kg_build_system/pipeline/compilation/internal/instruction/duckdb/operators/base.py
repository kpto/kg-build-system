"""Small helpers shared by expression emitters."""
from __future__ import annotations

from typing import TYPE_CHECKING

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..sql import SqlNode

from .......declaration.foundations.expressions.internal import OperationExpressionDTO

if TYPE_CHECKING:
    from ..protocols import EmissionContext, Operand


def require_arity(
    expression: OperationExpressionDTO,
    operands: Sequence[Operand[SqlNode]],
    expected: int,
    message: str,
) -> None:
    if len(operands) != expected:
        raise ValueError(message)


@dataclass(frozen=True, slots=True)
class BinaryEmitter:
    """An operator that renders two operands through one SQL constructor."""

    operator: str
    build: Callable[[SqlNode, SqlNode], SqlNode]
    message: str

    def emit(
        self,
        expression: OperationExpressionDTO,
        operands: Sequence[Operand[SqlNode]],
        context: EmissionContext[SqlNode],
    ) -> SqlNode:
        require_arity(expression, operands, 2, self.message)
        return self.build(operands[0].sql(), operands[1].sql())


def _split(text: SqlNode, separator: SqlNode) -> SqlNode:
    return exp.Anonymous(
        this="string_split",
        expressions=[text.copy(), separator.copy()],
    )


def _separator_parameters(
    expression: OperationExpressionDTO,
    operands: Sequence[Operand[SqlNode]],
    context: EmissionContext[SqlNode],
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


__all__ = ["BinaryEmitter", "require_arity"]
