"""Operators whose row effect is planned by the relational layer."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..nodes import SqlNode

from .....expressions.ir import OperationExpressionIR
from ....protocols import LoweringContext, Operand
from .base import require_arity


@dataclass(frozen=True, slots=True)
class Expand:
    operator = "expand"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        from .....relational.interfaces import expansion_scope

        return context.expansion(expansion_scope(expression))


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


OPERATORS = (Expand(), WherePresent(), WhereIf())

__all__ = ["OPERATORS"]
