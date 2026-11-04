"""Compile a graph blueprint into the core planner's workflow steps."""
from __future__ import annotations

from collections.abc import Sequence

from kg_build_system.distribution.executors.duckdb import DuckDbSqlEmitter
from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.data.service.internal import (
    plan_fields,
    plan_scan_sources,
    row_source_key,
)
from kg_build_system.kernel import PlanContext, RuntimeField, Step
from .artifacts import graph_record_components
from .plan import (
    declaration_fields,
    declared_read_paths,
    ordered_projections,
    ordered_row_source_plans,
)
from .relations import binding_sources, projection_sources
from .steps import (
    aggregation_steps,
    binding_step,
    projection_step,
    row_source_step,
    source_step,
)


class CorePlanner:
    """Plan sources, derived relations, bindings and graph records."""

    component_id = "core"
    version = "4"
    runtime_fields: tuple[RuntimeField, ...] = ()

    def __init__(self, *, engine: DuckDbSqlEmitter | None = None) -> None:
        self._engine = engine

    def plan(
        self, blueprint: GraphBlueprint, context: PlanContext,
    ) -> Sequence[Step]:
        """Return one source, row-source, projection, binding and aggregate step.

        Example:
            ```python
            steps = CorePlanner().plan(blueprint, PlanContext())
            ```
        """
        del context
        projections = ordered_projections(blueprint)
        used_tables: set[str] = set()
        for binding in blueprint.bindings:
            used_tables.update(binding_sources(binding))
        for projection in projections:
            used_tables.update(projection_sources(projection))
        sources = tuple(sorted(
            (
                source for source in blueprint.sources
                if source.table in used_tables
            ),
            key=lambda source: source.table,
        ))
        table_relations = {
            source.table: f"kg_table_{index}"
            for index, source in enumerate(sources)
        }
        read_paths = declared_read_paths(blueprint)
        projection_relations = {
            projection.name: f"kg_projection_{index}"
            for index, projection in enumerate(projections)
        }
        shapes = declaration_fields(blueprint)
        plans = ordered_row_source_plans(blueprint)
        row_source_relations = {
            row_source_key(plan): f"kg_rowsource_{index}"
            for index, plan in enumerate(plans)
        }
        row_source_fields = {
            row_source_key(plan): plan_fields(plan, shapes)
            for plan in plans
        }
        for plan in plans:
            for scan in plan_scan_sources(plan):
                if scan in shapes:
                    row_source_fields.setdefault(scan, shapes[scan])
        relations = table_relations | projection_relations | row_source_relations

        authored = [
            source_step(
                source, table_relations[source.table], blueprint, read_paths,
            )
            for source in sources
        ]
        authored.extend(
            row_source_step(
                plan,
                row_source_relations[row_source_key(plan)],
                relations,
                row_source_fields,
                projection_relations,
                row_source_relations,
                engine=self._engine,
            )
            for plan in plans
        )
        authored.extend(
            projection_step(
                blueprint,
                projection,
                projection_relations[projection.name],
                relations,
                projection_relations,
                row_source_relations,
                engine=self._engine,
            )
            for projection in projections
        )
        authored.extend(
            binding_step(
                blueprint,
                binding,
                index,
                relations,
                projection_relations,
                row_source_relations,
                engine=self._engine,
            )
            for index, binding in enumerate(blueprint.bindings)
        )
        authored.extend(aggregation_steps(blueprint))
        return tuple(authored)


__all__ = ["CorePlanner"]
