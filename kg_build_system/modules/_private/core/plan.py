"""What the core compiler needs to know about the blueprint before compiling.

This module owns ordering, the declaration shape map and the declared-null path
set. It does not build steps and it does not lower SQL.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ....compile.internal.ir import BuildBlueprint
from ....engines.internal import PARQUET_LIST_WRAPPER_PATH
from ....expressions.internal import walk_expression_ir
from ....expressions.internal.ir import FieldReferenceExpressionIR
from ....table.internal import struct_type_key
from ....table.internal.ir import ProjectionIR, RowScanIR, RowSourcePlanIR, StructIR
from ....types.internal.ir import ArrayTypeIR, NullableTypeIR, StructTypeIR
from .lowering import binding_outputs, projection_sources


def blueprint_from_context(context: Any) -> BuildBlueprint:
    """The blueprint a compiler reads, from its compatibility or kernel shape."""
    blueprint = getattr(context, "blueprint", None)
    if blueprint is not None:
        return blueprint
    build = getattr(context, "build", None)
    if build is None:
        raise ValueError("module compilation requires a blueprint or a build")
    return _blueprint_from_build(build)


def _part(build: Any, name: str) -> Any:
    part = getattr(build, "part", None)
    if callable(part):
        return part(name)
    try:
        return build.parts[name]
    except (AttributeError, KeyError) as error:
        raise ValueError(f"build has no language part {name!r}") from error


def _members(value: Any, name: str) -> tuple[Any, ...]:
    members = getattr(value, name, None)
    return tuple(value if members is None else members)


def _blueprint_from_build(build: Any) -> BuildBlueprint:
    data = _part(build, "data")
    topology = _part(build, "topology")
    binding = _part(build, "binding")
    return BuildBlueprint(
        structs=_members(data, "structs"),
        tables=_members(data, "tables"),
        components=_members(topology, "components"),
        projections=_members(data, "projections"),
        bindings=_members(binding, "bindings"),
        sources=_members(data, "sources"),
    )


def ordered_projections(blueprint: BuildBlueprint) -> tuple[ProjectionIR, ...]:
    """Projections in dependency order, each read after what it references."""
    pending = {projection.name: projection for projection in blueprint.projections}
    ordered: list[ProjectionIR] = []
    while pending:
        ready = sorted(
            (
                projection
                for projection in pending.values()
                if not (projection_sources(projection) & pending.keys())
            ),
            key=lambda projection: projection.symbol_id,
        )
        if not ready:
            raise ValueError("projection dependency graph contains a cycle")
        for projection in ready:
            ordered.append(projection)
            del pending[projection.name]
    return tuple(ordered)


def ordered_row_source_plans(
    blueprint: BuildBlueprint,
) -> tuple[RowSourcePlanIR, ...]:
    """Every derived plan once, children before the plans that read them."""
    roots = [
        item.row_source
        for item in (*blueprint.projections, *blueprint.bindings)
        if item.row_source is not None
    ]
    ordered: list[RowSourcePlanIR] = []
    seen: set[str] = set()

    def visit(plan: RowSourcePlanIR) -> None:
        key = row_source_key_of(plan)
        if key in seen:
            return
        seen.add(key)
        for child in plan_inputs_of(plan):
            visit(child)
        if not isinstance(plan, RowScanIR):
            ordered.append(plan)

    for plan in roots:
        visit(plan)
    return tuple(ordered)


def row_source_key_of(plan: RowSourcePlanIR) -> str:
    from ....table.internal import row_source_key

    return row_source_key(plan)


def plan_inputs_of(plan: RowSourcePlanIR) -> tuple[RowSourcePlanIR, ...]:
    from ....table.internal import plan_inputs

    return plan_inputs(plan)


def declaration_fields(blueprint: BuildBlueprint) -> dict[str, tuple[Any, ...]]:
    """The top-level field shape of every table and projection a plan can scan."""
    from ....table.internal import ShapeField

    fields = {
        item.name: tuple(
            ShapeField(field.name, field.name, field.logical_type)
            for field in item.fields
        )
        for item in blueprint.tables
    }
    fields.update({
        item.name: tuple(
            ShapeField(field.name, field.name, field.expression.logical_type)
            for field in item.fields
        )
        for item in blueprint.projections
    })
    return fields


def declared_non_null_paths(
    table: Any, structs: Mapping[tuple[str, str], StructIR],
) -> dict[tuple[str, ...], tuple[str, ...]]:
    """Every path the contract claims is non-null, by logical and schema form.

    The contract's array markers supply Parquet's list wrappers, so the schema
    form matches what ``parquet_metadata()`` reports as ``path_in_schema`` even
    for a member several expansions deep.
    """
    found: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    def walk(
        fields,
        prefix: tuple[str, ...],
        schema_prefix: tuple[str, ...],
        parents: frozenset[tuple[str, str]],
    ) -> None:
        for declared in fields:
            logical_type = declared.logical_type
            nullable = isinstance(logical_type, NullableTypeIR)
            base = logical_type.value if nullable else logical_type
            is_array = isinstance(base, ArrayTypeIR)
            item = base.item if is_array else base
            logical_path = (*prefix, declared.name)
            schema_path = (
                *schema_prefix, declared.name,
                *(PARQUET_LIST_WRAPPER_PATH if is_array else ()),
            )
            if not nullable:
                found.append((logical_path, schema_path))
            if isinstance(item, StructTypeIR):
                key = (item.module, item.qualname)
                if key not in parents:
                    declaration = structs.get(key)
                    if declaration is not None:
                        walk(
                            declaration.fields, logical_path, schema_path,
                            parents | {key},
                        )

    walk(table.fields, (), (), frozenset())
    return dict(found)


def declared_read_paths(
    blueprint: BuildBlueprint,
) -> dict[str, tuple[Any, ...]]:
    """The non-null-claiming contract paths this build reads, per table.

    The null-count pre-flight asks only about what is read: a forty-column table
    whose three used columns are clean should not fill a report with the
    thirty-seven nobody reads. A projection output is consumed whole, so the
    table columns feeding a consumed projection count as read too. Claimed paths
    come from the contract, so a nullable path never reaches the pre-flight.
    """
    from .ir import DeclaredPathIR

    tables = {table.name: table for table in blueprint.tables}
    structs = {
        key: struct
        for struct in blueprint.structs
        if (key := struct_type_key(struct)) is not None
    }
    projections = {projection.name: projection for projection in blueprint.projections}
    claims = {
        name: declared_non_null_paths(table, structs)
        for name, table in tables.items()
    }
    read: dict[str, set[tuple[str, ...]]] = {name: set() for name in tables}
    pending: list[Any] = [
        expression
        for binding in blueprint.bindings
        for expression in binding_outputs(binding).values()
    ]
    included: set[str] = set()
    while pending:
        for node in walk_expression_ir(pending.pop()):
            if not isinstance(node, FieldReferenceExpressionIR):
                continue
            if node.source in tables:
                read[node.source].add(node.path)
            elif node.source in projections and node.source not in included:
                included.add(node.source)
                pending.extend(
                    field.expression for field in projections[node.source].fields
                )

    def is_read(table_name: str, claimed: tuple[str, ...]) -> bool:
        """Whether the build reaches one claimed path.

        A reference to a nested value arrives as the outermost field plus a
        ``struct_field``/``expand`` operation over it, so a read of a prefix
        reaches everything below that prefix.
        """
        return any(claimed[:len(seen)] == seen for seen in read[table_name])

    return {
        table: tuple(
            DeclaredPathIR(
                schema_path=".".join(claims[table][path]),
                logical_path=".".join(path),
            )
            for path in sorted(
                claimed for claimed in claims[table] if is_read(table, claimed)
            )
        )
        for table in tables
        if any(is_read(table, claimed) for claimed in claims[table])
    }


__all__ = [
    "blueprint_from_context",
    "declaration_fields",
    "declared_non_null_paths",
    "declared_read_paths",
    "ordered_projections",
    "ordered_row_source_plans",
]
