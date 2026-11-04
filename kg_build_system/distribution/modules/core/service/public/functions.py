"""Public core planner helpers."""
from __future__ import annotations

from kg_build_system.distribution.modules.core.service._private.binding.service.public.planner import (
    BindingPlanner,
)
from kg_build_system.distribution.modules.core.service._private.input.service.public.planner import (
    InputPlanner,
)
from kg_build_system.distribution.modules.core.service._private.projection.service.public.planner import (
    ProjectionPlanner,
)
from kg_build_system.distribution.modules.core.service._private.records.service.public.planner import (
    RecordsPlanner,
)
from kg_build_system.distribution.modules.core.service._private.row_source.service.public.planner import (
    RowSourcePlanner,
)
from kg_build_system.distribution.modules.duckdb import DuckDbSqlEmitter


def core_planners(
    *, engine: DuckDbSqlEmitter | None = None,
) -> tuple[
    InputPlanner,
    RowSourcePlanner,
    ProjectionPlanner,
    BindingPlanner,
    RecordsPlanner,
]:
    """Return the five core planners in assembled plan order.

    Example:
        ```python
        from kg_build_system.distribution.modules.core import core_planners

        planners = core_planners()
        assert len(planners) == 5
        ```
    """
    return (
        InputPlanner(engine=engine),
        RowSourcePlanner(engine=engine),
        ProjectionPlanner(engine=engine),
        BindingPlanner(engine=engine),
        RecordsPlanner(engine=engine),
    )


__all__ = ["core_planners"]
