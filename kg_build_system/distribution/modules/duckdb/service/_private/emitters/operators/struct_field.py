"""Emit the ``struct_field`` expression operator."""
from __future__ import annotations

from typing import TYPE_CHECKING

from collections.abc import Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..sql import SqlNode

from kg_build_system.distribution.languages.expressions.model.internal import OperationExpressionDTO

if TYPE_CHECKING:
    from ..protocols import EmissionContext, Operand
from .base import require_arity
from ..sql import identifier


@dataclass(frozen=True, slots=True)
class StructField:
    operator = "struct_field"

    def emit(
        self,
        expression: OperationExpressionDTO,
        operands: Sequence[Operand[SqlNode]],
        context: EmissionContext[SqlNode],
    ) -> SqlNode:
        require_arity(
            expression, operands, 1, "struct_field requires one argument",
        )
        return exp.Dot(
            this=operands[0].sql(),
            expression=identifier(str(context.parameter(expression, "name"))),
        )


__all__ = ["StructField"]
