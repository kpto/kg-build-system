"""Render one derived relation's relational product."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kg_build_system.distribution.languages.data.model.internal import (
    DerivedRelationDTO,
)
from kg_build_system.distribution.modules.core.service._private.planning.emission import (
    product_sql,
    retarget_expression,
)
from kg_build_system.distribution.service.internal.emission import SqlEmitter


def derived_relation_sql(
    relations: Mapping[str, str],
    derived_relation: DerivedRelationDTO,
    *,
    engine: SqlEmitter,
    shapes: Mapping[str, Any] | None = None,
) -> str:
    """Render one derived relation's outputs through the SQL emitter."""
    outputs = {
        column.name: retarget_expression(
            column.expression, derived_relation.row_source,
        )
        for column in derived_relation.columns
        if column.expression is not None
    }
    return product_sql(outputs, relations, engine=engine, shapes=shapes)


__all__ = ["derived_relation_sql"]
