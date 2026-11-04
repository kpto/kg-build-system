"""The generic DuckDB source planner for asset-backed tables."""
from __future__ import annotations

from collections.abc import Sequence

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.kernel import PlanContext, RuntimeField, Step


class DuckDbSourcePlanner:
    """Plan one source-relation step for each compatible asset-backed table.

    The planner reads the logical asset of every table the graph uses and
    resolves that asset's descriptive layout to a physical location. It knows
    only the ``parquet``, ``json`` and ``csv`` formats; another module
    contributes another ordinary planner for another format.

    Example:
        ```python
        from kg_build_system.distribution.modules.duckdb import (
            DuckDbSourcePlanner,
        )

        planner = DuckDbSourcePlanner()
        steps = planner.plan(blueprint, PlanContext())
        ```
    """

    component_id = "duckdb"
    version = "1"
    runtime_fields: tuple[RuntimeField, ...] = ()

    def __init__(
        self,
        *,
        formats: Sequence[str] = ("parquet", "json", "csv"),
        union_by_name: bool = False,
    ) -> None:
        self._formats = frozenset(formats)
        self._union_by_name = union_by_name

    def plan(
        self, blueprint: GraphBlueprint, context: PlanContext,
    ) -> Sequence[Step]:
        """Return the source steps for this compile.

        Example:
            ```python
            steps = DuckDbSourcePlanner().plan(blueprint, PlanContext())
            ```
        """
        del context
        from .._private.planner import source_steps

        return source_steps(blueprint, formats=self._formats)


__all__ = ["DuckDbSourcePlanner"]
