"""Render one projection's relational product."""
from __future__ import annotations

from collections.abc import Mapping

from kg_build_system.distribution.languages.data.model.internal import (
    ProjectionDTO,
)
from kg_build_system.distribution.modules.core.service._private.planning.emission import (
    product_sql,
    retarget_expression,
)
from kg_build_system.distribution.service.internal.emission import SqlEmitter


def projection_sql(
    relations: Mapping[str, str],
    projection: ProjectionDTO,
    *,
    engine: SqlEmitter,
) -> str:
    """Render one projection's outputs through the configured SQL emitter."""
    outputs = {
        column.name: retarget_expression(column.expression, projection.row_source)
        for column in projection.columns
        if column.expression is not None
    }
    return product_sql(outputs, relations, engine=engine)


__all__ = ["projection_sql"]
