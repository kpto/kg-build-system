"""Emit the ``append`` expression operator.

``append`` has the same SQL contract as ``concat``; it exists as a named
operation for callers that prefer that spelling.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from collections.abc import Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..sql import SqlNode

from .......declaration.foundations.expressions.internal import OperationExpressionDTO

if TYPE_CHECKING:
    from ..protocols import EmissionContext, Operand


@dataclass(frozen=True, slots=True)
class Append:
    operator = "append"

    def emit(
        self,
        expression: OperationExpressionDTO,
        operands: Sequence[Operand[SqlNode]],
        context: EmissionContext[SqlNode],
    ) -> SqlNode:
        return exp.Anonymous(
            this="concat", expressions=[operand.sql() for operand in operands],
        )


__all__ = ["Append"]
