"""Emit the ``array_slice`` expression operator."""
from __future__ import annotations

from typing import TYPE_CHECKING

from collections.abc import Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..sql import SqlNode

from kg_build_system.declaration.foundations.expressions.model.internal import OperationExpressionDTO

if TYPE_CHECKING:
    from ..protocols import EmissionContext, Operand
from .base import require_arity


@dataclass(frozen=True, slots=True)
class ArraySlice:
    operator = "array_slice"

    def emit(
        self,
        expression: OperationExpressionDTO,
        operands: Sequence[Operand[SqlNode]],
        context: EmissionContext[SqlNode],
    ) -> SqlNode:
        require_arity(
            expression, operands, 3,
            "array_slice requires an array, a start and an end",
        )
        return exp.Anonymous(
            this="list_slice",
            expressions=[
                operands[0].sql(),
                exp.Add(
                    this=operands[1].sql(), expression=exp.Literal.number(1),
                ),
                operands[2].sql(),
            ],
        )


__all__ = ["ArraySlice"]
