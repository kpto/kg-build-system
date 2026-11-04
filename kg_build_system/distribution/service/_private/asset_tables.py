"""The asset-backed tables one graph build reads.

One asset can back many relations, so a source planner needs the logical
relation and the asset it comes from, not a per-table source binding. This
module decides which relations the graph actually reads and pairs each with its
asset descriptor and declared columns.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.asset.model.internal import (
    AssetDTO,
    AssetGovernanceDTO,
    AssetLayoutDTO,
    AssetLicenseDTO,
    AssetSemanticsDTO,
)
from kg_build_system.distribution.languages.asset.model.public import (
    AssetDescriptor,
    AssetGovernance,
    AssetLayout,
    AssetLicense,
    AssetSemantics,
)
from kg_build_system.distribution.languages.binding.model.internal import (
    BindingDTO,
    EdgeBindingDTO,
)
from kg_build_system.distribution.languages.data.model.internal import (
    ProjectionDTO,
    RelationDTO,
)
from kg_build_system.distribution.languages.data.service.internal import (
    plan_scan_sources,
)
from kg_build_system.distribution.languages.expressions.model.internal import (
    ExpressionDTO,
    FieldReferenceDTO,
)
from kg_build_system.distribution.languages.expressions.service.internal import (
    walk_expression_dto,
)
from kg_build_system.kernel.service.internal.types import type_from_dto
from ...model.public.asset_tables import AssetColumn, AssetTable


def _license(value: AssetLicenseDTO | None) -> AssetLicense | None:
    if value is None:
        return None
    return AssetLicense(
        identifier=value.identifier,
        url=value.url,
        attribution=value.attribution,
    )


def _governance(value: AssetGovernanceDTO) -> AssetGovernance:
    return AssetGovernance(
        license=_license(value.license),
        owner=value.owner,
        metadata=dict(value.metadata),
    )


def _layout(value: AssetLayoutDTO | None) -> AssetLayout | None:
    if value is None:
        return None
    return AssetLayout(
        kind=value.kind,
        locator=value.locator,
        format=value.format,
        selector=value.selector,
        partition_by=value.partition_by,
        members=dict(value.members),
        properties=dict(value.properties),
    )


def _semantics(value: AssetSemanticsDTO) -> AssetSemantics:
    return AssetSemantics(
        subject=value.subject,
        coverage=value.coverage,
        authority=value.authority,
        basis=value.basis,
        claims=value.claims,
        limitations=value.limitations,
        title=value.title,
        description=value.description,
    )


def asset_descriptor(value: AssetDTO) -> AssetDescriptor:
    """Convert one asset DTO into its authoring-independent descriptor."""
    return AssetDescriptor(
        name=value.name,
        website=value.website,
        version=value.version,
        layout=_layout(value.layout),
        semantics=_semantics(value.semantics),
        governance=_governance(value.governance),
    )


def _expression_relations(expressions: Iterable[ExpressionDTO | None]) -> set[str]:
    return {
        node.field.relation
        for expression in expressions
        if expression is not None
        for node in walk_expression_dto(expression)
        if isinstance(node, FieldReferenceDTO)
    }


def _binding_relations(binding: BindingDTO) -> set[str]:
    expressions: list[ExpressionDTO | None] = [binding.identity]
    if isinstance(binding, EdgeBindingDTO):
        expressions.extend((binding.source_identity, binding.target_identity))
    expressions.extend(expression for _, expression in binding.properties)
    found = _expression_relations(expressions)
    if binding.rows is not None:
        found.update(plan_scan_sources(binding.rows))
    return found


def _projection_relations(projection: ProjectionDTO) -> set[str]:
    found = _expression_relations(
        column.expression for column in projection.columns
    )
    found.update(plan_scan_sources(projection.row_source))
    return found


def _read_relations(blueprint: GraphBlueprint) -> set[str]:
    found: set[str] = set()
    for binding in blueprint.bindings:
        found.update(_binding_relations(binding))
    for projection in blueprint.data.projections:
        found.update(_projection_relations(projection))
    return found


def _used_tables(blueprint: GraphBlueprint) -> tuple[RelationDTO, ...]:
    relations = {item.name: item for item in blueprint.data.relations}
    return tuple(
        relations[name]
        for name in sorted(_read_relations(blueprint) & relations.keys())
    )


def _asset_for(blueprint: GraphBlueprint, relation: RelationDTO) -> AssetDescriptor:
    if relation.asset is None:
        raise ValueError(
            f"relation {relation.name!r} must name its logical asset"
        )
    for asset in blueprint.assets.assets:
        if asset.name == relation.asset.name:
            return asset_descriptor(asset)
    raise ValueError(
        f"relation {relation.name!r} names an unknown asset "
        f"{relation.asset.name!r}"
    )


def _table(blueprint: GraphBlueprint, index: int, relation: RelationDTO) -> AssetTable:
    return AssetTable(
        asset=_asset_for(blueprint, relation),
        relation=f"kg_table_{index}",
        relation_name=relation.name,
        columns=tuple(
            AssetColumn(column.name, type_from_dto(column.logical_type))
            for column in relation.columns
        ),
    )


def asset_tables(blueprint: GraphBlueprint) -> tuple[AssetTable, ...]:
    """Every asset-backed relation this graph reads, sorted by relation name."""
    return tuple(
        _table(blueprint, index, relation)
        for index, relation in enumerate(_used_tables(blueprint))
    )


def table_relations(blueprint: GraphBlueprint) -> Mapping[str, str]:
    """Map every table relation this graph reads to its plan relation name."""
    return MappingProxyType({
        table.relation_name: table.relation
        for table in asset_tables(blueprint)
    })


__all__ = [
    "AssetColumn", "AssetTable", "asset_descriptor", "asset_tables",
    "table_relations",
]
