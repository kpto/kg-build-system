"""Public DuckDB executor surface.

The emitter and executor implementations live in the package's private zone;
each function here is a thin delegation kept on the public service path.
"""
from __future__ import annotations

from collections.abc import Mapping

from kg_build_system.distribution.languages.expressions.model.internal import (
    ExpressionDTO,
)
from kg_build_system.distribution.languages.table.model.public.shapes import (
    ShapeField,
)
from kg_build_system.distribution.languages.table.model.internal import (
    RowSourcePlanDTO,
)

from ..internal import (
    ArraySqlType,
    DuckDbExecutor,
    DuckDbInstructionEmitter,
    DuckDbResourceProvider,
    DuckDbSqlEmitter,
    EmissionContext,
    ExpressionEmitter,
    Operand,
    RelationPlan,
    SqlType,
    expression_sql as _expression_sql,
    relation_sql as _relation_sql,
    row_source_sql as _row_source_sql,
)
from ...model.public import (
    RelationQueryResult,
    RelationRef,
    RelationService,
    canonical_sql_type,
)


def expression_sql(
    expression: ExpressionDTO,
    *,
    aliases: Mapping[str, str] | None = None,
    emitter: DuckDbInstructionEmitter | None = None,
) -> str:
    """Render one expression directly as DuckDB SQL text.

    Example:
        ```python
        sql = expression_sql(expression)
        ```
    """
    if emitter is None:
        return _expression_sql(expression, aliases=aliases)
    return _expression_sql(expression, aliases=aliases, emitter=emitter)


def relation_sql(
    plan: RelationPlan,
    *,
    emitter: DuckDbInstructionEmitter | None = None,
) -> str:
    """Render a self-contained relational product as DuckDB SQL.

    Example:
        ```python
        sql = relation_sql(plan)
        ```
    """
    if emitter is None:
        return _relation_sql(plan)
    return _relation_sql(plan, emitter=emitter)


def row_source_sql(
    plan: RowSourcePlanDTO,
    relations: Mapping[str, str],
    shapes: Mapping[str, tuple[ShapeField, ...]],
    *,
    emitter: DuckDbInstructionEmitter | None = None,
) -> str:
    """Render one row-source plan as DuckDB SQL text.

    Example:
        ```python
        sql = row_source_sql(plan, relations, shapes)
        ```
    """
    if emitter is None:
        return _row_source_sql(plan, relations, shapes)
    return _row_source_sql(plan, relations, shapes, emitter=emitter)


__all__ = [
    "ArraySqlType",
    "DuckDbExecutor",
    "DuckDbInstructionEmitter",
    "DuckDbResourceProvider",
    "DuckDbSqlEmitter",
    "EmissionContext",
    "ExpressionEmitter",
    "Operand",
    "RelationQueryResult",
    "RelationRef",
    "RelationService",
    "SqlType",
    "canonical_sql_type",
    "expression_sql",
    "relation_sql",
    "row_source_sql",
]
