"""Context shared by row-source lowerers."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from sqlglot import exp

from ..nodes import SqlNode

from .....expressions.ir import ExpressionIR
from .....table.interfaces import ShapeField, row_source_key
from ....protocols import ExpressionLowerer
from ..context import DuckDBLoweringContext


@dataclass(frozen=True, slots=True)
class PlanContext:
    relations: Mapping[str, str]
    shapes: Mapping[str, tuple[ShapeField, ...]]
    operators: Mapping[str, ExpressionLowerer[SqlNode]]

    def source_key(self, plan: object) -> str:
        return row_source_key(plan)  # type: ignore[arg-type]

    def relation_for(self, plan: object) -> str:
        return self.relations[self.source_key(plan)]

    def shape_for(self, plan: object) -> tuple[ShapeField, ...]:
        return self.shapes[self.source_key(plan)]

    def lower_expression(
        self, expression: ExpressionIR, aliases: Mapping[str, str],
    ) -> SqlNode:
        return DuckDBLoweringContext(self.operators, aliases=aliases).lower(
            expression
        )


__all__ = ["PlanContext"]
