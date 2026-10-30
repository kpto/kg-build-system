"""Struct expression operators."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..nodes import SqlNode

from .....expressions.ir import OperationExpressionIR
from ....protocols import LoweringContext, Operand
from .base import require_arity
from ..sql import identifier


@dataclass(frozen=True, slots=True)
class StructField:
    operator = "struct_field"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        require_arity(
            expression, operands, 1, "struct_field requires one argument",
        )
        return exp.Dot(
            this=operands[0].sql(),
            expression=identifier(str(context.parameter(expression, "name"))),
        )


OPERATORS = (StructField(),)

__all__ = ["OPERATORS"]
