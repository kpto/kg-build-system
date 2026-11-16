"""What the core planners need to know about the graph blueprint.

``CorePlan`` is the one plan four planners share through
``PlanContext.shared["core.plan"]``. ``CorePlanning`` computes it once: relation
names, row-source fields, derived relations, row-source plans and bindings. It does not
build steps and does not emit SQL.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.binding.model.internal.dto import (
    BindingDTO,
)
from kg_build_system.distribution.languages.data.model.internal import (
    DerivedRelationDTO,
    RowScanDTO,
    RowSourcePlanDTO,
)
from kg_build_system.distribution.languages.data.model.public.shapes import (
    ShapeField,
)
from kg_build_system.kernel.service.internal.types import type_from_dto
from kg_build_system.distribution.languages.data.service.internal import (
    plan_fields,
    plan_inputs,
    plan_scan_sources,
    row_source_key,
)
from kg_build_system.distribution.service.internal import table_relations
from kg_build_system.distribution.modules.core.service._private.planning.emission import (
    derived_relation_sources,
)
from kg_build_system.kernel import PlanContext

CORE_PLAN_KEY = "core.plan"


@dataclass(frozen=True, slots=True)
class CorePlan:
    """Everything the four core planners share for one compile."""

    derived_relation_dtos: tuple[DerivedRelationDTO, ...]
    row_source_plans: tuple[RowSourcePlanDTO, ...]
    bindings: tuple[BindingDTO, ...]
    shapes: Mapping[str, tuple[ShapeField, ...]]
    table_relations: Mapping[str, str]
    derived_relations: Mapping[str, str]
    row_source_relations: Mapping[str, str]
    row_source_fields: Mapping[str, tuple[ShapeField, ...]]
    relations: Mapping[str, str]


def ordered_derived_relations(
    blueprint: GraphBlueprint,
) -> tuple[DerivedRelationDTO, ...]:
    """Derived relations in dependency order, read after what they reference."""
    pending = {
        derived_relation.name: derived_relation
        for derived_relation in blueprint.data.derived_relations
    }
    ordered: list[DerivedRelationDTO] = []
    while pending:
        ready = sorted(
            (
                derived_relation
                for derived_relation in pending.values()
                if not (
                    derived_relation_sources(derived_relation) & pending.keys()
                )
            ),
            key=lambda derived_relation: derived_relation.name,
        )
        if not ready:
            raise ValueError("derived relation dependency graph contains a cycle")
        for derived_relation in ready:
            ordered.append(derived_relation)
            del pending[derived_relation.name]
    return tuple(ordered)


def ordered_row_source_plans(
    blueprint: GraphBlueprint,
) -> tuple[RowSourcePlanDTO, ...]:
    """Every derived plan once, children before the plans that read them."""
    roots = [
        item.row_source
        for item in blueprint.data.derived_relations
        if item.row_source is not None
    ]
    roots.extend(
        binding.rows
        for binding in blueprint.bindings
        if binding.rows is not None
    )
    ordered: list[RowSourcePlanDTO] = []
    seen: set[str] = set()

    def visit(plan: RowSourcePlanDTO) -> None:
        key = row_source_key(plan)
        if key in seen:
            return
        seen.add(key)
        for child in plan_inputs(plan):
            visit(child)
        if not isinstance(plan, RowScanDTO):
            ordered.append(plan)

    for plan in roots:
        visit(plan)
    return tuple(ordered)


def declaration_fields(
    blueprint: GraphBlueprint,
) -> dict[str, tuple[ShapeField, ...]]:
    """The top-level field shape of every relation a plan scans."""
    fields = {
        item.name: tuple(
            ShapeField(
                field.name, field.name, type_from_dto(field.logical_type),
            )
            for field in item.columns
        )
        for item in blueprint.data.source_relations
    }
    fields.update({
        item.name: tuple(
            ShapeField(
                field.name, field.name, type_from_dto(field.logical_type),
            )
            for field in item.columns
        )
        for item in blueprint.data.derived_relations
    })
    return fields


class CorePlanning:
    """Compute the shared core plan once for one blueprint."""

    def plan(self, blueprint: GraphBlueprint) -> CorePlan:
        """Return the relation, shape and binding facts of one build."""
        derived_relation_dtos = ordered_derived_relations(blueprint)
        relations_by_name = table_relations(blueprint)
        derived_relations = {
            derived_relation.name: f"kg_projection_{index}"
            for index, derived_relation in enumerate(derived_relation_dtos)
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
        relations = {
            **relations_by_name, **derived_relations, **row_source_relations,
        }
        return CorePlan(
            derived_relation_dtos=derived_relation_dtos,
            row_source_plans=plans,
            bindings=tuple(blueprint.bindings),
            shapes=shapes,
            table_relations=relations_by_name,
            derived_relations=derived_relations,
            row_source_relations=row_source_relations,
            row_source_fields=row_source_fields,
            relations=relations,
        )


def core_plan(
    blueprint: GraphBlueprint,
    context: PlanContext,
) -> CorePlan:
    """Read the shared core plan, building it on first use in this compile."""
    existing = context.shared.get(CORE_PLAN_KEY)
    if existing is None:
        existing = CorePlanning().plan(blueprint)
        context.shared[CORE_PLAN_KEY] = existing
    if not isinstance(existing, CorePlan):
        raise TypeError(
            f"{CORE_PLAN_KEY!r} must hold a CorePlan, not "
            f"{type(existing).__qualname__}"
        )
    return existing


__all__ = [
    "CORE_PLAN_KEY",
    "CorePlan",
    "CorePlanning",
    "core_plan",
    "declaration_fields",
    "ordered_derived_relations",
    "ordered_row_source_plans",
]
