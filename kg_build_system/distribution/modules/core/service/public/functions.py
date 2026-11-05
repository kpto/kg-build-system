"""Public core planner helpers."""
from __future__ import annotations

from kg_build_system.distribution.modules.core.binding.service.public.planner import (
    BindingPlanner,
)
from kg_build_system.distribution.modules.core.projection.service.public.planner import (
    ProjectionPlanner,
)
from kg_build_system.distribution.modules.core.records.service.public.planner import (
    RecordsPlanner,
)
from kg_build_system.distribution.modules.core.row_source.service.public.planner import (
    RowSourcePlanner,
)
from kg_build_system.distribution.service.internal.emission import SqlEmitter


def core_planners(
    *, engine: SqlEmitter,
) -> tuple[
    RowSourcePlanner,
    ProjectionPlanner,
    BindingPlanner,
    RecordsPlanner,
]:
    """Return the four core planners in assembled plan order.

    The generic DuckDB source planner is not a core planner; it is added by the
    default toolchain before this group. The caller supplies the engine's SQL
    emitter; the composition root injects the DuckDB one by default.

    Example:
        ```python
        from kg_build_system.distribution.modules.core import core_planners
        from kg_build_system.distribution.modules.duckdb import DuckDbSqlEmitter

        planners = core_planners(engine=DuckDbSqlEmitter())
        assert len(planners) == 4
        ```
    """
    return (
        RowSourcePlanner(engine=engine),
        ProjectionPlanner(engine=engine),
        BindingPlanner(engine=engine),
        RecordsPlanner(engine=engine),
    )


__all__ = ["core_planners"]
