"""Render one row-source plan with the DuckDB instruction emitter."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kg_build_system.distribution.languages.data.model.internal import (
    RowSourcePlanDTO,
)
from kg_build_system.distribution.modules.core.service._private.planning.emission import (
    instruction_emitter,
)
from kg_build_system.distribution.modules.duckdb.service.internal.emitters import (
    DuckDbSqlEmitter,
    row_source_sql as emit_row_source_sql,
)


def row_source_sql(
    plan: RowSourcePlanDTO,
    relations: Mapping[str, str],
    shapes: Mapping[str, Any],
    *,
    engine: DuckDbSqlEmitter | None = None,
) -> str:
    """Render one row-source plan with the supplied SQL emitter."""
    return emit_row_source_sql(
        plan, relations, shapes, emitter=instruction_emitter(engine),
    )


__all__ = ["row_source_sql"]
