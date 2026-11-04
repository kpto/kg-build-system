"""The declared read paths a generic source step promises to open.

Only paths the graph contract claims are non-null and the build actually
reaches are opened; the rest are recorded as limits rather than invented. This
is a source-planner concern, so it lives with the DuckDB source planner rather
than with the core relational planners.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from kg_build_system.distribution.languages.binding.model.internal import (
    BindingDTO,
    EdgeBindingDTO,
)
from kg_build_system.distribution.languages.data.model.internal import (
    ColumnDTO,
    RelationDTO,
    StructDTO,
)
from kg_build_system.distribution.languages.expressions.model.internal import (
    ExpressionDTO,
    FieldReferenceDTO,
)
from kg_build_system.distribution.languages.expressions.service.internal import (
    walk_expression_dto,
)
from kg_build_system.distribution.modules.duckdb.service.internal.emitters import (
    PARQUET_LIST_WRAPPER_PATH,
)
from kg_build_system.kernel.model.internal.types.dto import (
    ArrayTypeDTO,
    NullableTypeDTO,
    StructTypeDTO,
)


@dataclass(frozen=True, slots=True)
class DeclaredPath:
    """One declared member path, in both forms the source step needs."""

    schema_path: str
    logical_path: str


def _snake_name(value: str) -> str:
    """The blueprint's logical name for a generated struct class name."""
    import re

    text = value.rsplit(".", 1)[-1]
    if text.endswith("Struct"):
        text = text[:-len("Struct")]
    return re.sub(r"(?<!^)(?=[A-Z])", "_", text).lower()


def _struct_name(value: StructTypeDTO) -> str:
    return _snake_name(value.qualname)


def _structs(blueprint: Any) -> dict[str, StructDTO]:
    return {struct.name: struct for struct in blueprint.data.structs}


def _binding_outputs(binding: BindingDTO) -> dict[str, ExpressionDTO]:
    outputs: dict[str, ExpressionDTO] = {"build_key": binding.identity}
    if isinstance(binding, EdgeBindingDTO):
        outputs["source_build_key"] = binding.source_identity
        outputs["target_build_key"] = binding.target_identity
    outputs.update(dict(binding.properties))
    return outputs


def declared_non_null_paths(
    relation: RelationDTO, structs: Mapping[str, StructDTO],
) -> dict[tuple[str, ...], tuple[str, ...]]:
    """Every path the contract claims is non-null, by logical and schema form."""
    found: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    def walk(
        columns: tuple[ColumnDTO, ...],
        prefix: tuple[str, ...],
        schema_prefix: tuple[str, ...],
        parents: frozenset[str],
    ) -> None:
        for declared in columns:
            logical_type = declared.logical_type
            nullable = isinstance(logical_type, NullableTypeDTO)
            base = logical_type.value if nullable else logical_type
            is_array = isinstance(base, ArrayTypeDTO)
            item = base.item if is_array else base
            logical_path = (*prefix, declared.name)
            schema_path = (
                *schema_prefix, declared.name,
                *(PARQUET_LIST_WRAPPER_PATH if is_array else ()),
            )
            if not nullable:
                found.append((logical_path, schema_path))
            if isinstance(item, StructTypeDTO):
                struct_name = _struct_name(item)
                if struct_name not in parents:
                    declaration = structs.get(struct_name)
                    if declaration is not None:
                        walk(
                            declaration.columns, logical_path, schema_path,
                            parents | {struct_name},
                        )

    walk(relation.columns, (), (), frozenset())
    return dict(found)


def declared_read_paths(blueprint: Any) -> dict[str, tuple[DeclaredPath, ...]]:
    """The non-null-claiming contract paths this build reads, per relation."""
    relations = {
        relation.name: relation for relation in blueprint.data.relations
    }
    structs = _structs(blueprint)
    projections = {
        projection.name: projection
        for projection in blueprint.data.projections
    }
    claims = {
        name: declared_non_null_paths(relation, structs)
        for name, relation in relations.items()
    }
    read: dict[str, set[tuple[str, ...]]] = {
        name: set() for name in relations
    }
    pending: list[Any] = [
        expression
        for binding in blueprint.bindings
        for expression in _binding_outputs(binding).values()
    ]
    included: set[str] = set()
    while pending:
        for node in walk_expression_dto(pending.pop()):
            if not isinstance(node, FieldReferenceDTO):
                continue
            source = node.field.relation
            if source in relations:
                read[source].add((node.field.field, *node.path))
            elif source in projections and source not in included:
                included.add(source)
                pending.extend(
                    column.expression
                    for column in projections[source].columns
                    if column.expression is not None
                )

    def is_read(relation_name: str, claimed: tuple[str, ...]) -> bool:
        """Whether the build reaches one claimed path."""
        return any(
            claimed[:len(seen)] == seen for seen in read[relation_name]
        )

    return {
        relation: tuple(
            DeclaredPath(
                schema_path=".".join(claims[relation][path]),
                logical_path=".".join(path),
            )
            for path in sorted(
                claimed
                for claimed in claims[relation]
                if is_read(relation, claimed)
            )
        )
        for relation in relations
        if any(is_read(relation, claimed) for claimed in claims[relation])
    }


__all__ = [
    "DeclaredPath",
    "declared_non_null_paths",
    "declared_read_paths",
]
