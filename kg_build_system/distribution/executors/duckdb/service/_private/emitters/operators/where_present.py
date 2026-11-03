"""Emit the ``where_present`` expression operator."""
from __future__ import annotations

from typing import TYPE_CHECKING

from collections.abc import Sequence
from dataclasses import dataclass

from ..sql import SqlNode

from kg_build_system.distribution.languages.expressions.model.internal import OperationExpressionDTO

if TYPE_CHECKING:
    from ..protocols import EmissionContext, Operand
from .base import require_arity


@dataclass(frozen=True, slots=True)
class WherePresent:
    operator = "where_present"

    def emit(
        self,
        expression: OperationExpressionDTO,
        operands: Sequence[Operand[SqlNode]],
        context: EmissionContext[SqlNode],
    ) -> SqlNode:
        require_arity(
            expression, operands, 1, "where_present requires one argument",
        )
        return operands[0].sql()


__all__ = ["WherePresent"]
