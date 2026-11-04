"""Context shared by row-source emitters."""
from __future__ import annotations

from typing import TYPE_CHECKING

from collections.abc import Mapping
from dataclasses import dataclass

from sqlglot import exp

from ..sql import SqlNode

from kg_build_system.distribution.languages.expressions.model.internal import ExpressionDTO
from kg_build_system.distribution.languages.data.service.internal import row_source_key
from kg_build_system.distribution.languages.data.model.public import ShapeField

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
