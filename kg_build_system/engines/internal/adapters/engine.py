"""Foreign-interface adapter: the DuckDB engine behind the neutral ``Engine``."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any, ClassVar

from ....expressions.internal.ir import ExpressionIR
from ....relational.internal.ir import RelationPlanIR
from ....table.internal import ShapeField
from ....table.internal.ir import RowSourcePlanIR
from ..protocols import ExpressionLowerer, RowSourceLowerer
from ..._private.duckdb.engine import (
    DEFAULT_LOWERING,
    DuckDBLowering,
    lower_expression,
    lower_expression_sql,
    lower_plan,
    lower_row_source,
)
from ..._private.duckdb.sql import SqlNode


@dataclass(frozen=True, slots=True)
class DuckDBEngine:
    """The DuckDB implementation of the engine-neutral lowering contract."""

    name: ClassVar[str] = "duckdb"
    lowering: DuckDBLowering = DEFAULT_LOWERING

    @property
    def operators(self) -> Mapping[str, ExpressionLowerer[SqlNode]]:
        return self.lowering.operators

    @property
    def row_sources(self) -> Mapping[type[Any], RowSourceLowerer[SqlNode]]:
        return self.lowering.row_sources

    def with_operators(
        self, *lowerers: ExpressionLowerer[SqlNode],
    ) -> "DuckDBEngine":
        return replace(self, lowering=self.lowering.with_operators(*lowerers))

    def with_row_sources(
        self, *lowerers: RowSourceLowerer[SqlNode],
    ) -> "DuckDBEngine":
        return replace(
            self, lowering=self.lowering.with_row_sources(*lowerers),
        )

    def lower_expression(
        self,
        expression: ExpressionIR,
        *,
        aliases: Mapping[str, str] | None = None,
        expansions: Mapping[tuple[str, ...], SqlNode] | None = None,
    ) -> SqlNode:
        return lower_expression(
            expression,
            aliases=aliases,
            expansions=expansions,
            lowering=self.lowering,
        )

    def lower_expression_sql(
        self, expression: ExpressionIR, *,
        aliases: Mapping[str, str] | None = None,
    ) -> str:
        return lower_expression_sql(
            expression, aliases=aliases, lowering=self.lowering,
        )

    def lower_plan(self, plan: RelationPlanIR) -> str:
        return lower_plan(plan, lowering=self.lowering)

    def lower(self, plan: RelationPlanIR) -> str:
        """Alias for :meth:`lower_plan`."""
        return self.lower_plan(plan)

    def lower_relation_sql(self, plan: RelationPlanIR) -> str:
        return lower_plan(plan, lowering=self.lowering)

    def lower_row_source(
        self,
        plan: RowSourcePlanIR,
        relations: Mapping[str, str],
        shapes: Mapping[str, tuple[ShapeField, ...]],
    ) -> str:
        return lower_row_source(
            plan, relations, shapes, lowering=self.lowering,
        )

    def lower_row_source_sql(
        self,
        plan: RowSourcePlanIR,
        relations: Mapping[str, str],
        shapes: Mapping[str, tuple[ShapeField, ...]],
    ) -> str:
        return lower_row_source(
            plan, relations, shapes, lowering=self.lowering,
        )

    def configure(self, connection: Any) -> None:
        """Create the framework macros on a build connection."""
        from ..._private.duckdb.service import configure_framework_macros

        configure_framework_macros(connection)

    configure_macros = configure

    def relation_service(
        self, connection: Any, *, checkpoint_on_step: bool = False,
    ) -> Any:
        """Wrap one connection in the engine's single-worker relation service."""
        from ..._private.duckdb.service import DuckDBRelationService

        return DuckDBRelationService(
            connection, checkpoint_on_step=checkpoint_on_step,
        )

    service = relation_service


DEFAULT_ENGINE = DuckDBEngine()

__all__ = ["DEFAULT_ENGINE", "DuckDBEngine"]
