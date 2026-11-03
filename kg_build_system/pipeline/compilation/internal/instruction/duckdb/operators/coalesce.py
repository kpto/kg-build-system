"""Emit the ``coalesce`` expression operator."""
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
class Coalesce:
    operator = "coalesce"

    def emit(
        self,
        expression: OperationExpressionDTO,
        operands: Sequence[Operand[SqlNode]],
        context: EmissionContext[SqlNode],
    ) -> SqlNode:
        if len(operands) < 2:
            raise ValueError("coalesce requires at least two arguments")
        return exp.Coalesce(
            this=operands[0].sql(),
            expressions=[operand.sql() for operand in operands[1:]],
        )


__all__ = ["Coalesce"]
