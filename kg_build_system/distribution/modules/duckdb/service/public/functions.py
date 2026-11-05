"""Public DuckDB SQL rendering helpers."""
from __future__ import annotations

from collections.abc import Mapping

from kg_build_system.distribution.languages.data.model.internal import (
    RowSourcePlanDTO,
)
from kg_build_system.distribution.languages.data.model.public.shapes import (
    ShapeField,
)
from kg_build_system.distribution.languages.expressions.model.internal import (
    ExpressionDTO,
)
from kg_build_system.distribution.service.internal.emission import RelationPlan

from ..internal import (
    DuckDbInstructionEmitter,
    expression_sql as _expression_sql,
    relation_sql as _relation_sql,
    row_source_sql as _row_source_sql,
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


__all__ = ["expression_sql", "relation_sql", "row_source_sql"]
