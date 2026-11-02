"""Lower the ``append`` expression operator.

``append`` has the same SQL contract as ``concat``; it exists as a named
operation for callers that prefer that spelling.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from collections.abc import Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..sql import SqlNode

from .....expressions.internal.ir import OperationExpressionIR

if TYPE_CHECKING:
    from ....internal.protocols import LoweringContext, Operand


@dataclass(frozen=True, slots=True)
class Append:
    operator = "append"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        return exp.Anonymous(
            this="concat", expressions=[operand.sql() for operand in operands],
        )


__all__ = ["Append"]
