"""Emit the ``transform_items`` expression operator."""
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
class TransformItems:
    operator = "transform_items"

    def emit(
        self,
        expression: OperationExpressionDTO,
        operands: Sequence[Operand[SqlNode]],
        context: EmissionContext[SqlNode],
    ) -> SqlNode:
        require_arity(
            expression, operands, 2, "transform_items requires two arguments",
        )
        item = exp.column("_kg_item", quoted=False)
        item_name = context.parameter(expression, "item")
        body = context.with_variable(item_name, item).emit(
            expression.arguments[1]
        )
        return exp.Anonymous(
            this="list_transform",
            expressions=[
                operands[0].sql(),
                exp.Lambda(this=body, expressions=[item.copy()]),
            ],
        )


__all__ = ["TransformItems"]
