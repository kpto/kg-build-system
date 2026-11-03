"""Build generated shapes from DuckDB descriptions and Parquet node trees."""
from __future__ import annotations

from collections.abc import Iterator, Sequence
import re
from typing import cast

from .....kernel.internal.types import UnitTypeName, is_canonical_unit_name
from ...internal.generated import (
    GeneratedArrayType, GeneratedClass, GeneratedField, GeneratedNullableType,
    GeneratedScalarType, GeneratedStructType, GeneratedType, Nullability,
    ScalarTypeName,
)
from ...internal.models import GenerationError
from .formats import PARQUET_LIST_WRAPPERS
from .mapping import (
    DeclaredOnlyDigest, RefusedDigest, canonical_sql_type, digest_for,
)
from .naming import Paths, record_name, top_level_column
from .nullability import level_nullability, wrap
from .observation import DescribedColumn, ParquetSchemaRow

type ParquetTreeNodeRow = tuple[str, str, str | None, int | None, str | None, int]
from .overrides import (
    container_promotion, overridden_field, promoted_type_name, promotion_declaration,
)
from .state import Inference

_FIXED_ARRAY_ITEM = re.compile(r"(?s)^(.*)\[\d+\]$")


def split_top_level(value: str, separator: str = ",") -> tuple[str, ...]:
    result: list[str] = []
    depth = 0
    start = 0
    for index, character in enumerate(value):
        if character in "([<":
            depth += 1
        elif character in ")]>":
            depth -= 1
        elif character == separator and depth == 0:
            result.append(value[start:index].strip())
            start = index + 1
    result.append(value[start:].strip())
    return tuple(part for part in result if part)


def is_struct_text(type_name: str) -> bool:
    normalized = type_name.strip()
    return normalized.upper().startswith("STRUCT(") and normalized.endswith(")")


def array_item_text(type_name: str) -> str | None:
    """The item type a flattened DuckDB type string names for an array, if any."""
    normalized = type_name.strip()
    if normalized.endswith("[]"):
        return normalized[:-2].strip() or None
    match = _FIXED_ARRAY_ITEM.match(normalized)
    return (match.group(1).strip() or None) if match else None


def struct_member_texts(type_name: str) -> dict[str, str]:
    if not is_struct_text(type_name):
        return {}
    result: dict[str, str] = {}
    for member in split_top_level(type_name.strip()[7:-1]):
        match = re.match(r'(?s)^(?:"((?:[^"]|"")+)"|([^ ]+))\s+(.+)$', member)
        if match is None:
            raise GenerationError(
                f"cannot interpret struct member {member!r} in column {type_name!r}"
            )
        result[(match.group(1) or match.group(2) or "").replace('""', '"')] = match.group(3)
    return result


class ParquetNode:
    """One node of a Parquet schema tree, in the file's own naming."""

    __slots__ = ("name", "repetition", "duckdb_type", "children")

    def __init__(
        self, name: str, repetition: str, duckdb_type: str | None,
        children: tuple["ParquetNode", ...],
    ) -> None:
        self.name = name
        self.repetition = repetition
        self.duckdb_type = duckdb_type
        self.children = children

    @property
    def declared(self) -> bool:
        return self.repetition.upper() == "REQUIRED"

    @property
    def repeated(self) -> bool:
        return self.repetition.upper() == "REPEATED"

    def __repr__(self) -> str:
        return f"<{self.name} {self.repetition} {self.duckdb_type} {len(self.children)}>"


def fold_parquet_schema(rows: Sequence[ParquetTreeNodeRow]) -> tuple[ParquetNode, ...]:
    """Fold one file's flat ``parquet_schema()`` rows into a node tree.

    Rows arrive in pre-order depth-first order and a group owns the
    ``num_children`` subtrees that follow it. The first node is the root — DuckDB
    names it ``duckdb_schema`` — and it carries the top-level columns.
    """
    position = 0

    def parse() -> ParquetNode:
        nonlocal position
        name, repetition, _physical, children, duckdb_type, _column_id = rows[position]
        position += 1
        return ParquetNode(
            name, repetition, duckdb_type,
            tuple(parse() for _ in range(children or 0)),
        )

    root = parse()
    if position != len(rows):
        raise GenerationError("Parquet schema nodes did not form a single tree")
    return root.children


def walk_nodes(nodes: Sequence[ParquetNode]) -> Iterator[ParquetNode]:
    for node in nodes:
        yield node
        yield from walk_nodes(node.children)


def node_shape(nodes: Sequence[ParquetNode]) -> tuple[tuple[str, str, str | None], ...]:
    return tuple(
        (node.name, node.repetition.upper(), node.duckdb_type)
        for node in walk_nodes(nodes)
    )


def parquet_trees(rows: Sequence[ParquetSchemaRow]) -> tuple[ParquetNode, ...]:
    """Parse every file of one source and require the files to agree.

    A partitioned source is only inferrable while every file declares the same
    nodes; silently taking the first file would hide a schema change in one
    partition behind a contract the other partitions violate.
    """
    grouped: dict[str, list[ParquetTreeNodeRow]] = {}
    for row in rows:
        grouped.setdefault(row[0], []).append(row[1:])
    if not grouped:
        raise GenerationError("parquet_schema() returned no schema for the given source")
    trees = {name: fold_parquet_schema(tuple(items)) for name, items in grouped.items()}
    reference_name, reference = next(iter(trees.items()))
    reference_shape = node_shape(reference)
    for name, tree in trees.items():
        if node_shape(tree) != reference_shape:
            raise GenerationError(
                "the Parquet files of this relation declare different schemas: "
                f"{reference_name!r} and {name!r} disagree; a partitioned source can "
                "only be inferred while every file agrees"
            )
    return reference


def _require_not_refused(type_name: str, *, path: str) -> None:
    """Refuse a type the digest gate refuses, whichever authority reported it."""
    digest = digest_for(type_name)
    if isinstance(digest, RefusedDigest):
        raise GenerationError(
            f"column {path!r} has DuckDB type {type_name!r}, which is rejected: "
            f"{digest.reason}. Either export the column in a mappable type, or "
            "declare this table outside a generated package."
        )


def resolve_scalar(type_name: str, *, path: str, column: str | None = None) -> ScalarTypeName:
    """Map one DuckDB type name to a logical scalar through the digest gate.

    The gate decides whether the type is usable as it stands, usable only
    through an author declaration because the only cast narrows, or refused
    with a reason. An unknown name is a fourth case and stays fail-closed.
    """
    digest = digest_for(type_name)
    if digest is None:
        raise GenerationError(f"column {path!r} has unsupported type {type_name!r}")
    if isinstance(digest, RefusedDigest):
        raise GenerationError(
            f"column {path!r} has DuckDB type {type_name!r}, which is rejected: "
            f"{digest.reason}. Either export the column in a mappable type, or "
            "declare this table outside a generated package."
        )
    if isinstance(digest, DeclaredOnlyDigest):
        declared = canonical_sql_type(cast(UnitTypeName, digest.canonical))
        if column is None:
            remedy = (
                f"export the member as {declared} or declare this table outside a "
                "generated package: an override reaches top-level columns only"
            )
            subject = "member"
        else:
            remedy = (
                f"{promotion_declaration(column, str(digest.canonical))} on this "
                "request is the override, and the checked cast the scan then "
                "applies fails the build on a value that does not fit"
            )
            subject = "column"
        raise GenerationError(
            f"column {path!r} has DuckDB type {type_name!r}, which reaches the "
            f"canonical type {digest.canonical!r} only by narrowing: {digest.narrowing}. "
            "The ingest boundary widens and never narrows by itself, so this "
            f"{subject} needs a declared override saying that {declared} is the "
            f"type meant; {remedy}."
        )
    if not is_canonical_unit_name(digest.canonical):
        raise GenerationError(
            f"column {path!r} has DuckDB type {type_name!r}, which digests to the "
            f"canonical {digest.canonical!r} shape: a container is digested from "
            "its item or member types rather than as a scalar, so the reported "
            "type and the shape it belongs to do not fit each other."
        )
    return ScalarTypeName(digest.canonical)


def _register(inferred: GeneratedField, paths: Paths, inference: Inference) -> GeneratedField:
    if len(paths.logical) > 1:
        inference.nested_members.update(paths.logical[1:])
    return inferred


def make_field(name: str, paths: Paths, value_type: GeneratedType, *, inference: Inference) -> GeneratedField:
    nullability = (
        Nullability.DEFAULTED if isinstance(value_type, GeneratedNullableType)
        else Nullability.DECLARED
    )
    from .naming import identifier

    return _register(
        GeneratedField(
            identifier(name), name, value_type, nullability=nullability,
            schema_path=paths.schema_text, logical_path=paths.logical_text,
        ),
        paths, inference,
    )


def shape_for_node(
    *, node: ParquetNode, paths: Paths, describe_type: str, inference: Inference,
) -> tuple[GeneratedType, tuple[GeneratedClass, ...], bool]:
    """One node's shape, its nested declarations, and whether it is nullable.

    One recursion covers scalar, list and record alike, which is what lets an
    array of arrays be read correctly: DuckDB nests the three-level list
    convention inside itself, so ``VARCHAR[][]`` arrives as
    ``list / element / list / element`` and each level is one more array.
    """
    _require_not_refused(describe_type, path=paths.logical_text)
    if not node.children:
        scalar = resolve_scalar(
            describe_type, path=paths.logical_text, column=top_level_column(paths),
        )
        return GeneratedScalarType(scalar), (), not node.declared

    if is_list_node(node):
        wrapper = node.children[0]
        if not wrapper.repeated:
            raise GenerationError(
                f"column {paths.logical_text!r} is shaped like a Parquet list but "
                f"its {wrapper.name!r} wrapper is not REPEATED"
            )
        item_type, declarations, item_nullable = item_of_list(
            wrapper=wrapper, paths=paths, describe_type=describe_type,
            inference=inference,
        )
        return (
            GeneratedArrayType(
                wrap(item_type, Nullability.DEFAULTED) if item_nullable else item_type
            ),
            declarations,
            not node.declared,
        )

    struct_name = record_name(paths)
    described = struct_member_texts(describe_type)
    members: list[GeneratedField] = []
    nested: list[GeneratedClass] = []
    for child in node.children:
        field_, child_declarations = tree_field(
            node=child, paths=paths.child(child.name),
            describe_type=member_type(
                described, child, describe_type=describe_type, paths=paths,
            ),
            inference=inference,
        )
        members.append(field_)
        nested.extend(child_declarations)
    nested.append(GeneratedClass(struct_name, tuple(members), base="Struct"))
    return GeneratedStructType(struct_name), tuple(nested), not node.declared


def member_type(
    described: dict[str, str], child: ParquetNode, *,
    describe_type: str, paths: Paths,
) -> str:
    """The type one record member is reported as, by either authority."""
    reported = described.get(child.name) or child.duckdb_type
    if reported is None:
        raise GenerationError(
            f"member {paths.child(child.name).logical_text!r} is declared by the "
            f"Parquet footer, but {describe_type!r} names no type for it and the "
            "footer carries none either; the two views of this file do not agree "
            "about its shape"
        )
    return reported


def item_type_text(describe_type: str, carrier: ParquetNode, *, paths: Paths) -> str:
    """The type one list item is reported as, by either authority."""
    reported = array_item_text(describe_type) or carrier.duckdb_type
    if reported is None:
        raise GenerationError(
            f"column {paths.logical_text!r} is a list in the Parquet footer, but "
            f"{describe_type!r} names no item type and the {carrier.name!r} node "
            "carries none either; the two views of this file do not agree about "
            "its shape"
        )
    return reported


def item_of_list(
    *, wrapper: ParquetNode, paths: Paths, describe_type: str, inference: Inference,
) -> tuple[GeneratedType, tuple[GeneratedClass, ...], bool]:
    """The item shape of a REPEATED wrapper, and whether that item is nullable."""
    if not wrapper.children:
        item_paths = paths.child(wrapper.name)
        scalar = resolve_scalar(
            item_type_text(describe_type, wrapper, paths=paths),
            path=item_paths.logical_text,
        )
        return GeneratedScalarType(scalar), (), not wrapper.declared
    element = wrapper.children[0]
    item_paths = paths.child(wrapper.name, element.name)
    item_type, declarations, item_nullable = shape_for_node(
        node=element, paths=item_paths,
        describe_type=item_type_text(describe_type, element, paths=paths),
        inference=inference,
    )
    return item_type, declarations, item_nullable


def tree_field(
    *, node: ParquetNode, paths: Paths, describe_type: str, inference: Inference,
) -> tuple[GeneratedField, tuple[GeneratedClass, ...]]:
    """One member whose shape comes from the Parquet node tree."""
    shape, declarations, _shape_is_nullable = shape_for_node(
        node=node, paths=paths, describe_type=describe_type, inference=inference,
    )
    value = wrap(shape, level_nullability(node.repetition))
    return make_field(node.name, paths, value, inference=inference), declarations


def is_list_node(node: ParquetNode) -> bool:
    return (
        bool(node.children) and len(node.children) <= 2
        and any(child.name in PARQUET_LIST_WRAPPERS for child in node.children)
    )


def text_item_shape(
    *, type_name: str, paths: Paths, inference: Inference,
) -> tuple[GeneratedType, tuple[GeneratedClass, ...]]:
    """Resolve the item shape carried by a flattened ``DESCRIBE`` type string."""
    normalized = type_name.strip()
    item = array_item_text(normalized)
    if item is not None:
        return text_item_shape(type_name=item, paths=paths, inference=inference)
    item_paths = paths.child("element") if paths.logical[-1] != "element" else paths
    if not is_struct_text(normalized):
        scalar = resolve_scalar(normalized, path=item_paths.logical_text)
        return GeneratedScalarType(scalar), ()
    struct_name = record_name(item_paths)
    members: list[GeneratedField] = []
    nested: list[GeneratedClass] = []
    for member_name, member_type_text in struct_member_texts(normalized).items():
        field_, declarations = text_field(
            name=member_name, type_name=member_type_text, nullability=Nullability.DEFAULTED,
            paths=item_paths.child(member_name), inference=inference,
        )
        members.append(field_)
        nested.extend(declarations)
    nested.append(GeneratedClass(struct_name, tuple(members), base="Struct"))
    return GeneratedStructType(struct_name), tuple(nested)


def text_field(
    *, name: str, type_name: str, nullability: Nullability,
    paths: Paths, inference: Inference,
) -> tuple[GeneratedField, tuple[GeneratedClass, ...]]:
    """One member inferred from a ``DESCRIBE`` type string, nullability included."""
    normalized = type_name.strip()
    declarations: tuple[GeneratedClass, ...] = ()
    if array_item_text(normalized) is not None:
        item, declarations = text_item_shape(
            type_name=normalized, paths=paths, inference=inference,
        )
        # A flattened type string names no nullability at any level, so an item
        # of a schema-less array is nullable too.
        if not isinstance(item, GeneratedNullableType):
            item = GeneratedNullableType(item)
        value: GeneratedType = GeneratedArrayType(item)
    elif is_struct_text(normalized):
        struct_name = record_name(paths)
        members: list[GeneratedField] = []
        nested: list[GeneratedClass] = []
        for member_name, member_type_text in struct_member_texts(normalized).items():
            field_, member_declarations = text_field(
                name=member_name, type_name=member_type_text,
                nullability=Nullability.DEFAULTED,
                paths=paths.child(member_name), inference=inference,
            )
            members.append(field_)
            nested.extend(member_declarations)
        nested.append(GeneratedClass(struct_name, tuple(members), base="Struct"))
        value = GeneratedStructType(struct_name)
        declarations = tuple(nested)
    else:
        scalar = resolve_scalar(
            normalized, path=paths.logical_text, column=top_level_column(paths),
        )
        value = GeneratedScalarType(scalar)

    return make_field(name, paths, wrap(value, nullability), inference=inference), declarations


def members(
    *,
    described: tuple[DescribedColumn, ...],
    nodes: tuple[ParquetNode, ...],
    sources: tuple[str, ...],
    relation_path: str,
    inference: Inference,
) -> tuple[tuple[GeneratedField, tuple[GeneratedClass, ...]], ...]:
    """One finished member per DuckDB column, with the source's own shape.

    The two authorities stay separate: DuckDB's own read decides which columns
    exist and what scalar each holds, and — for Parquet only —
    ``parquet_schema()`` decides nested structure and nullability at every
    level. A DuckDB column that no file declares, such as a hive partition
    key, is ``DEFAULTED``; a node the read does not expose means the two views
    of the file disagree, which fails.
    """
    by_column = {node.name: node for node in nodes}
    unbacked = sorted(set(by_column) - {column.name for column in described})
    if unbacked:
        raise GenerationError(
            "parquet_schema() declares "
            + ", ".join(repr(name) for name in unbacked)
            + f" of {sources[0]!r}, which DuckDB's read of the same file does not expose"
        )
    result: list[tuple[GeneratedField, tuple[GeneratedClass, ...]]] = []
    for column in described:
        name, type_name, nullability = column.name, column.type_name, column.nullability
        node = by_column.get(name)
        paths = Paths((name,), (name,))
        key = f"{relation_path}.{name}"
        override = inference.overrides.get(key)
        if override is not None:
            inference.consumed.add(key)
            if override.type is not None:
                canonical = cast(UnitTypeName, override.type)
                if node is not None and node.children:
                    raise container_promotion(type_name, column=name, canonical=canonical)
                type_name = promoted_type_name(type_name, column=name, canonical=canonical)
        field_, nested = (
            text_field(
                name=name, type_name=type_name, nullability=nullability,
                paths=paths, inference=inference,
            ) if node is None else tree_field(
                node=node, paths=paths, describe_type=type_name, inference=inference,
            )
        )
        if override is not None and override.nullable is not None:
            field_ = overridden_field(field_, override.nullable)
        result.append((field_, nested))
    return tuple(result)


__all__ = [
    "ParquetNode", "array_item_text", "fold_parquet_schema", "is_struct_text",
    "item_of_list", "item_type_text", "make_field", "member_type", "members",
    "node_shape", "parquet_trees", "resolve_scalar", "shape_for_node",
    "split_top_level", "struct_member_texts", "text_field", "text_item_shape",
    "tree_field", "walk_nodes",
]
