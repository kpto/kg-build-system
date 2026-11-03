"""Core workflow compilation: plan the blueprint and author its steps."""
from __future__ import annotations

from typing import Any

from ....declaration.blueprint.public import GraphBlueprint
from ....declaration.languages.table.internal import (
    plan_fields,
    plan_scan_sources,
    row_source_key,
)
from ....kernel import (
    CompilationContext,
    ModuleCompiler,
)
from ....pipeline.contract.public import (
    ContributionDTO,
    ModuleDefinitionDTO,
    ModuleReferenceDTO,
)
from .module import CoreModule
from .plan import (
    blueprint_from_context,
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


class CoreCompiler(ModuleCompiler):
    """Compile sources, derived relations, bindings and graph records."""

    async def compile(
        self, context: CompilationContext[Any],
    ) -> ContributionDTO:
        blueprint: GraphBlueprint = blueprint_from_context(context)
        definition = ModuleDefinitionDTO(
            reference=ModuleReferenceDTO(
                module_id=CoreModule.ID,
                import_module=CoreModule.__module__,
                class_qualname=CoreModule.__qualname__,
                implementation_version=CoreModule.VERSION,
                configuration={},
            )
        )
        projections = ordered_projections(blueprint)
        used_tables = set()
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
            source_step(source, table_relations[source.table], blueprint, read_paths)
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
            )
            for index, binding in enumerate(blueprint.bindings)
        )
        authored.extend(aggregation_steps(blueprint))
        return ContributionDTO(definition, tuple(authored))


__all__ = ["CoreCompiler"]
