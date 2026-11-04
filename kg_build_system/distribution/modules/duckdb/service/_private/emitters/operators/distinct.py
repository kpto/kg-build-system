"""Emit the ``distinct`` expression operator."""
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


@dataclass(frozen=True, slots=True)
class Distinct:
    operator = "distinct"

    def emit(
        self,
        expression: OperationExpressionDTO,
        operands: Sequence[Operand[SqlNode]],
        context: EmissionContext[SqlNode],
    ) -> SqlNode:
        require_arity(expression, operands, 1, "distinct requires one argument")
        return exp.Anonymous(this="list_distinct", expressions=[operands[0].sql()])


__all__ = ["Distinct"]
