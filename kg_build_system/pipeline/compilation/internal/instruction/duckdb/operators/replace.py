"""Emit the ``replace`` expression operator."""
from __future__ import annotations

from typing import TYPE_CHECKING

from collections.abc import Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..sql import SqlNode

from .......declaration.foundations.expressions.internal import OperationExpressionDTO

if TYPE_CHECKING:
    from ..protocols import EmissionContext, Operand
from .base import require_arity


@dataclass(frozen=True, slots=True)
class Replace:
    operator = "replace"

    def emit(
        self,
        expression: OperationExpressionDTO,
        operands: Sequence[Operand[SqlNode]],
        context: EmissionContext[SqlNode],
    ) -> SqlNode:
        require_arity(expression, operands, 3, "replace requires three arguments")
        return exp.Anonymous(
            this="replace", expressions=[operand.sql() for operand in operands],
        )


__all__ = ["Replace"]
