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
from kg_build_system.distribution.service.internal.emission import SqlEmitter


def row_source_sql(
    plan: RowSourcePlanDTO,
    relations: Mapping[str, str],
    shapes: Mapping[str, Any],
    *,
    engine: SqlEmitter,
) -> str:
    """Render one row-source plan with the supplied SQL emitter."""
    return instruction_emitter(engine).emit_row_source(
        plan, relations, shapes,
    )


__all__ = ["row_source_sql"]
