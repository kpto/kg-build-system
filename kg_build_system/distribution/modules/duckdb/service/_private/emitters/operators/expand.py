"""Emit the ``expand`` expression operator."""
from __future__ import annotations

from typing import TYPE_CHECKING

from collections.abc import Sequence
from dataclasses import dataclass

from ..sql import SqlNode

from kg_build_system.distribution.languages.expressions.model.internal import OperationExpressionDTO

if TYPE_CHECKING:
    from ..protocols import EmissionContext, Operand


@dataclass(frozen=True, slots=True)
class Expand:
    operator = "expand"

    def emit(
        self,
        expression: OperationExpressionDTO,
        operands: Sequence[Operand[SqlNode]],
        context: EmissionContext[SqlNode],
    ) -> SqlNode:
        from ..planning import expansion_scope

        return context.expansion(expansion_scope(expression))


__all__ = ["Expand"]
