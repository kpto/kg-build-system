"""Context shared by row-source emitters."""
from __future__ import annotations

from typing import TYPE_CHECKING

from collections.abc import Mapping
from dataclasses import dataclass

from sqlglot import exp

from ..sql import SqlNode

from .......declaration.foundations.expressions.internal import ExpressionDTO
from .......declaration.languages.table.internal import row_source_key
from .......declaration.languages.table.public import ShapeField

if TYPE_CHECKING:
    from ..protocols import ExpressionEmitter
from ..context import DuckDbExpressionContext


@dataclass(frozen=True, slots=True)
class PlanContext:
    relations: Mapping[str, str]
    shapes: Mapping[str, tuple[ShapeField, ...]]
    operators: Mapping[str, ExpressionEmitter[SqlNode]]

    def source_key(self, plan: object) -> str:
        return row_source_key(plan)  # type: ignore[arg-type]

    def relation_for(self, plan: object) -> str:
        return self.relations[self.source_key(plan)]

    def shape_for(self, plan: object) -> tuple[ShapeField, ...]:
        return self.shapes[self.source_key(plan)]

    def expression_context(
        self, aliases: Mapping[str, str],
    ) -> DuckDbExpressionContext:
        return DuckDbExpressionContext(self.operators, aliases=aliases)

    def emit_expression(
        self, expression: ExpressionDTO, aliases: Mapping[str, str],
    ) -> SqlNode:
        return self.expression_context(aliases).emit(expression)


__all__ = ["PlanContext"]
