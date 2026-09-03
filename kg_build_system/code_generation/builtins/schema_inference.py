"""Infer edit-time data contracts from supported data inputs."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import keyword
import logging
from pathlib import Path, PurePosixPath
import re
from typing import Any, ClassVar, Final, Iterator, Literal, Sequence
from urllib.parse import urlparse

import duckdb
import fsspec
from fsspec import AbstractFileSystem

from ..models import (
    GeneratedArrayType,
    GeneratedClass,
    GeneratedField,
    GeneratedFile,
    GeneratedMember,
    GeneratedNullableType,
    GeneratedPackage,
    GeneratedScalarType,
    GeneratedStructType,
    GeneratedType,
    GenerationError,
    Nullability,
    NullabilityNote,
    ProviderGenerationConfig,
    ScalarTypeName,
)
from ..providers import Provider, ProviderContext
from ...engines.duckdb import (
    PARQUET_LIST_WRAPPERS as _LIST_WRAPPERS,
    DeclaredOnlyDigest,
    RefusedDigest,
    canonical_sql_type,
    digest_for,
    read_declared_null_statistics,
    read_parquet_schema_rows,
)
from ...types import (
    CANONICAL_UNIT_NAMES,
    UnitTypeName,
    is_canonical_unit_name,
)


def _reader(connection: duckdb.DuckDBPyConnection):
    """Adapt a DuckDB connection to the read-only query contract."""
    def read(query: str, parameters: Sequence[object]) -> Sequence[Sequence[Any]]:
        return connection.execute(query, list(parameters)).fetchall()

    return read

_LOGGER = logging.getLogger("kg_build_system.code_generation.inference")

_DATABASE_SUFFIXES = {".db", ".ddb", ".duckdb"}
_REMOTE_SCHEMES = {"http", "https", "s3"}
_DATA_SUFFIXES = {".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".parquet", ".pq"}
_PARQUET_SUFFIXES = {".parquet", ".pq"}
_HIVE_PARTITION = re.compile(r"^[^/=]+=[^/]+$")

#: The three levels of schema trust of SOURCE_SCHEMA_TRUST_AND_NULLABILITY_SPEC.md section 3.
SchemaTier = Literal["enforced", "declared", "defaulted"]


def _identifier(value: str, *, fallback: str = "field") -> str:
    result = re.sub(r"[^A-Za-z0-9_]", "_", value)
    result = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", result).lower().strip("_") or fallback
    if result[0].isdigit():
        result = f"{fallback}_{result}"
    if keyword.iskeyword(result) or result == "options":
        result += "_"
    return result


def _class_part(value: str) -> str:
    words = [part for part in re.split(r"[^A-Za-z0-9]+", value) if part]
    result = "".join(part[:1].upper() + part[1:] for part in words) or "Relation"
    return f"Relation{result}" if result[0].isdigit() else result


def _split_top_level(value: str, separator: str = ",") -> tuple[str, ...]:
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


def _is_struct_text(type_name: str) -> bool:
    normalized = type_name.strip()
    return normalized.upper().startswith("STRUCT(") and normalized.endswith(")")


#: A fixed-size array is reported as ``INTEGER[3]``, so its item is whatever
#: precedes either bracket.
_FIXED_ARRAY_ITEM = re.compile(r"(?s)^(.*)\[\d+\]$")


def _array_item_text(type_name: str) -> str | None:
    """The item type a flattened DuckDB type string names for an array, if any.

    ``None`` says the string carries no array at all, which is not the same thing
    as a string naming an item of its own: the caller then needs the type the
    Parquet node carries, and failing that has to report the disagreement.
    """
    normalized = type_name.strip()
    if normalized.endswith("[]"):
        return normalized[:-2].strip() or None
    match = _FIXED_ARRAY_ITEM.match(normalized)
    return (match.group(1).strip() or None) if match else None


def _tier_for_suffix(suffix: str) -> SchemaTier:
    """One tier decision per source, per section 3 of the trust specification."""
    if suffix in _DATABASE_SUFFIXES:
        return "enforced"
    if suffix in _PARQUET_SUFFIXES:
        return "declared"
    return "defaulted"


def _describe_nullability(tier: SchemaTier, describe_reports_nullable: bool) -> Nullability:
    """Map ``DESCRIBE``'s ``null`` column according to the source tier.

    That column reports only *enforced* ``NOT NULL`` catalog constraints, so it is
    silent about what a file declares: a table-function scan answers ``YES`` for
    every column whether or not the file marks it ``required``. Only an enforced
    store may therefore yield non-nullability here, and Parquet is overridden
    from ``parquet_schema()`` afterwards.
    """
    if tier != "enforced":
        return Nullability.DEFAULTED
    return Nullability.DEFAULTED if describe_reports_nullable else Nullability.ENFORCED


def _rejected(type_name: str, path: str, reason: str) -> GenerationError:
    return GenerationError(
        f"column {path!r} has DuckDB type {type_name!r}, which is rejected: {reason}. "
        "Either export the column in a mappable type, or declare this table "
        "outside a generated package."
    )


#: The scope limit of a promotion, recorded by decision 9 of
#: ``DUCKDB_TYPE_IMPLEMENTATION_PLAN.md``. It is a decision the plan has not made
#: rather than a mistake a request can be corrected to avoid, so it is told rather
#: than reported as an absent column.
_NESTED_PROMOTION: Final = (
    "a promotion declares the canonical type of one top-level column, and nested "
    "promotion would need read_json(columns={...}), which replaces sniffing with a "
    "declared schema and moves the source's nullability from defaulted to declared "
    "— a separate decision"
)


def _promotion_declaration(column: str, canonical: str) -> str:
    """The request text that declares one top-level column's canonical type."""
    return f"promote={{{column!r}: {canonical!r}}}"


def _container_promotion(
    type_name: str, *, column: str, canonical: UnitTypeName,
) -> GenerationError:
    """A promotion names one canonical unit type, which no container has.

    The shape of a container is digested from the item or member types below it, so
    declaring a unit for the column itself would leave them undeclared while the
    contract read as a scalar.
    """
    return GenerationError(
        f"column {column!r} is read as {type_name!r}, a container whose shape is "
        f"digested from the types below it, so "
        f"{_promotion_declaration(column, canonical)} has no single canonical type "
        "of the column to declare; a promotion covers a column the reader reports "
        "as a scalar"
    )


def _promoted_type_name(
    type_name: str, *, column: str, canonical: UnitTypeName,
) -> str:
    """The type one top-level column is resolved from once a promotion declares it.

    A promotion says what the author means a column to hold; it does not make a
    refused physical type digestible, because refusal means no meaning-preserving
    canonical form exists rather than that no declaration has been made yet. The
    narrowing a declared-only type asks for is the declaration that gate reserves
    for an author, so a promotion is it, and the checked cast the scan then applies
    is what fails the build on a value that does not fit.
    """
    if _array_item_text(type_name) is not None or _is_struct_text(type_name):
        raise _container_promotion(type_name, column=column, canonical=canonical)
    digest = digest_for(type_name)
    if digest is None:
        raise GenerationError(f"column {column!r} has unsupported type {type_name!r}")
    if isinstance(digest, RefusedDigest):
        raise GenerationError(
            f"column {column!r} has DuckDB type {type_name!r}, which is rejected: "
            f"{digest.reason}. A rejection is not a gate a declaration lifts: it "
            "says no meaning-preserving canonical type exists for the values the "
            f"source holds, so {_promotion_declaration(column, canonical)} cannot "
            "be honoured. Either export the column in a mappable type, or declare "
            "this table outside a generated package."
        )
    if not is_canonical_unit_name(digest.canonical):
        raise _container_promotion(type_name, column=column, canonical=canonical)
    return canonical_sql_type(canonical)


def _declared_promotions(promote: dict[str, str]) -> dict[str, UnitTypeName]:
    """The promotion declarations of one request, checked as far as the source-free
    part of a decision reaches.

    A target has to be a canonical unit name because it becomes a declaration in the
    contract, and a key has to name a top-level column whatever the source turns out
    to hold. Whether such a column exists is a fact about the source, settled later.
    """
    declared: dict[str, UnitTypeName] = {}
    for column, canonical in sorted(promote.items()):
        if not is_canonical_unit_name(canonical):
            raise GenerationError(
                f"{_promotion_declaration(column, canonical)} does not name a "
                "canonical unit type; a promotion declares one of "
                + ", ".join(repr(name) for name in sorted(CANONICAL_UNIT_NAMES))
            )
        if "." in column:
            raise GenerationError(
                f"promote names {column!r}, which is a path rather than a column "
                f"name; {_NESTED_PROMOTION}"
            )
        declared[column] = canonical
    return declared


def _require_promoted_columns(inference: _Inference) -> None:
    """Settle each promotion against the columns the source actually reported.

    A key naming nothing is a typo or a request left stale by the data; a key naming
    a member of a column is the plan's own scope limit, and is told as such instead
    of being reported beside columns it could have named.
    """
    for column in sorted(set(inference.promote) - inference.promoted):
        if column in inference.nested_members:
            raise GenerationError(
                f"promote names {column!r}, which the source reports only as a "
                f"member of a column, not as a column; {_NESTED_PROMOTION}"
            )
        available = "; ".join(
            f"relation {relation!r} exposes "
            + ", ".join(repr(name) for name in sorted(names))
            for relation, names in sorted(inference.columns.items())
        ) or "no relation was inferred"
        raise GenerationError(
            f"promote names {column!r}, which is not a column the source reports; "
            f"{available}. A promotion declares a column the reader reports, so it "
            "has to name one of those"
        )


def _top_level_column(paths: _Paths) -> str | None:
    """The column a member is, when it is one, since only a column can be promoted."""
    return paths.logical[0] if len(paths.logical) == 1 else None


def _resolve_scalar(
    type_name: str, *, path: str, column: str | None = None,
) -> ScalarTypeName:
    """Map one DuckDB type name to a logical scalar through the digest gate.

    The gate is the engine's table, not a copy of it here, so a decision is made
    once for every DuckDB type: digestible as it stands, digestible only through
    an author declaration because the only cast narrows, or refused with a reason.
    An unknown name is a fourth case, and stays fail-closed.

    ``column`` is what the member is when it is a top-level column, which decides
    whether the declaration a declared-only type asks for can be named in terms an
    author can actually write.
    """
    digest = digest_for(type_name)
    if digest is None:
        raise GenerationError(f"column {path!r} has unsupported type {type_name!r}")
    if isinstance(digest, RefusedDigest):
        raise _rejected(type_name, path, digest.reason)
    if isinstance(digest, DeclaredOnlyDigest):
        declared = canonical_sql_type(digest.canonical)
        if column is None:
            remedy = (
                f"export the member as {declared} or declare this table outside a "
                "generated package: an override reaches top-level columns only"
            )
            subject = "member"
        else:
            remedy = (
                f"{_promotion_declaration(column, str(digest.canonical))} on this "
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


def _wrap(value: GeneratedType, nullability: Nullability) -> GeneratedType:
    if nullability is Nullability.DEFAULTED and not isinstance(value, GeneratedNullableType):
        return GeneratedNullableType(value)
    return value


def _struct_member_texts(type_name: str) -> dict[str, str]:
    if not _is_struct_text(type_name):
        return {}
    result: dict[str, str] = {}
    for member in _split_top_level(type_name.strip()[7:-1]):
        match = re.match(r'(?s)^(?:"((?:[^"]|"")+)"|([^ ]+))\s+(.+)$', member)
        if match is None:
            raise GenerationError(
                f"cannot interpret struct member {member!r} in column {type_name!r}"
            )
        result[(match.group(1) or match.group(2) or "").replace('""', '"')] = match.group(3)
    return result


@dataclass(frozen=True, slots=True)
class _Paths:
    """The two path forms one inferred member is recorded under.

    ``schema`` names every Parquet node, including the ``list``/``element``
    wrappers, which is the form ``parquet_metadata()`` reports in
    ``path_in_schema``; ``logical`` drops them, which is the form a report shows
    an author.
    """

    schema: tuple[str, ...]
    logical: tuple[str, ...]

    def child(self, *parts: str) -> "_Paths":
        return _Paths((*self.schema, *parts), (*self.logical, *parts))

    @property
    def schema_text(self) -> str:
        return ".".join(self.schema)

    @property
    def logical_text(self) -> str:
        return ".".join(self.logical)


@dataclass
class _Inference:
    """State shared by one generation pass.

    ``used_names`` is scoped per relation rather than per pass: two tables in one
    group may legitimately have a column of the same name, while two columns of
    one relation may not collide. The promotion state is scoped per pass instead,
    because a request declares a promotion once for the whole of what it generates.
    """

    declared_paths: set[str] = field(default_factory=set)
    used_names: dict[str, str] = field(default_factory=dict)
    promote: dict[str, UnitTypeName] = field(default_factory=dict)
    promoted: set[str] = field(default_factory=set)
    columns: dict[str, set[str]] = field(default_factory=dict)
    nested_members: set[str] = field(default_factory=set)


def _register(
    inferred: GeneratedField, paths: _Paths, inference: _Inference,
) -> GeneratedField:
    """Record the paths one finished member claims, for the statistics pre-flight."""
    if len(paths.logical) > 1:
        inference.nested_members.update(paths.logical[1:])
    if inferred.nullability is not Nullability.DEFAULTED:
        inference.declared_paths.add(inferred.schema_path or paths.schema_text)
    return inferred


def _make_field(
    name: str, paths: _Paths, value_type: GeneratedType, *, inference: _Inference,
) -> GeneratedField:
    nullability = (
        Nullability.DEFAULTED if isinstance(value_type, GeneratedNullableType)
        else Nullability.DECLARED
    )
    return _register(
        GeneratedField(
            _identifier(name), name, value_type, nullability=nullability,
            schema_path=paths.schema_text, logical_path=paths.logical_text,
        ),
        paths, inference,
    )


class _ParquetNode:
    """One node of a Parquet schema tree, in the file's own naming."""

    __slots__ = ("name", "repetition", "duckdb_type", "children")

    def __init__(
        self, name: str, repetition: str, duckdb_type: str | None,
        children: tuple["_ParquetNode", ...],
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


def _fold_parquet_schema(
    rows: Sequence[tuple[str, str, str | None, int | None, str | None, int]],
) -> tuple[_ParquetNode, ...]:
    """Fold one file's flat ``parquet_schema()`` rows into a node tree.

    Rows arrive in pre-order depth-first order and a group owns the
    ``num_children`` subtrees that follow it. The first node is the root — DuckDB
    names it ``duckdb_schema`` — and it carries the top-level columns.
    """
    position = 0

    def parse() -> _ParquetNode:
        nonlocal position
        name, repetition, _physical, children, duckdb_type, _column_id = rows[position]
        position += 1
        return _ParquetNode(
            name, repetition, duckdb_type,
            tuple(parse() for _ in range(children or 0)),
        )

    root = parse()
    if position != len(rows):
        raise GenerationError("Parquet schema nodes did not form a single tree")
    return root.children


def _walk_nodes(nodes: Sequence[_ParquetNode]) -> Iterator[_ParquetNode]:
    for node in nodes:
        yield node
        yield from _walk_nodes(node.children)


def _node_shape(nodes: Sequence[_ParquetNode]) -> tuple[tuple[str, str, str | None], ...]:
    return tuple(
        (node.name, node.repetition.upper(), node.duckdb_type)
        for node in _walk_nodes(nodes)
    )


def _parquet_trees(
    connection: duckdb.DuckDBPyConnection, sources: tuple[str, ...],
) -> tuple[_ParquetNode, ...]:
    """Parse every file of one source and require the files to agree (decision D3).

    A partitioned source is only inferrable while every file declares the same
    nodes; silently taking the first file would hide a schema change in one
    partition behind a contract the other partitions violate.
    """
    rows = read_parquet_schema_rows(_reader(connection), sources)
    grouped: dict[str, list[tuple[str, str, str | None, int | None, str | None, int]]] = {}
    for file_name, name, repetition, physical, children, duckdb_type, column_id in rows:
        grouped.setdefault(file_name, []).append(
            (name, repetition, physical, children, duckdb_type, column_id)
        )
    if not grouped:
        located = ", ".join(repr(item) for item in sources) or "the given source"
        raise GenerationError(
            f"parquet_schema() returned no schema for {located}"
        )
    trees = {name: _fold_parquet_schema(tuple(items)) for name, items in grouped.items()}
    reference_name, reference = next(iter(trees.items()))
    reference_shape = _node_shape(reference)
    for name, tree in trees.items():
        if _node_shape(tree) != reference_shape:
            raise GenerationError(
                "the Parquet files of this relation declare different schemas: "
                f"{reference_name!r} and {name!r} disagree; a partitioned source can "
                "only be inferred while every file agrees"
            )
    return reference


def _require_not_refused(type_name: str, *, path: str) -> None:
    """Refuse a type the digest gate refuses, whichever authority reported it.

    The node tree decides the shape and ``DESCRIBE`` decides the type, so a
    refused family has to be refused before the tree reads it: a ``MAP`` footer
    looks exactly like a record of a ``key`` and a ``value`` member.
    """
    digest = digest_for(type_name)
    if isinstance(digest, RefusedDigest):
        raise _rejected(type_name, path, digest.reason)


def _shape_for_node(
    *, node: _ParquetNode, paths: _Paths, describe_type: str, inference: _Inference,
) -> tuple[GeneratedType, tuple[GeneratedClass, ...], bool]:
    """One node's shape, its nested declarations, and whether it is nullable.

    One recursion covers scalar, list and record alike, which is what lets an
    array of arrays be read correctly: DuckDB nests the three-level list
    convention inside itself, so ``VARCHAR[][]`` arrives as
    ``list / element / list / element`` and each level is one more array.
    """
    _require_not_refused(describe_type, path=paths.logical_text)
    if not node.children:
        scalar = _resolve_scalar(
            describe_type, path=paths.logical_text, column=_top_level_column(paths),
        )
        return GeneratedScalarType(scalar), (), not node.declared

    if _is_list_node(node):
        wrapper = node.children[0]
        if not wrapper.repeated:
            raise GenerationError(
                f"column {paths.logical_text!r} is shaped like a Parquet list but "
                f"its {wrapper.name!r} wrapper is not REPEATED"
            )
        item_type, declarations, item_nullable = _item_of_list(
            wrapper=wrapper, paths=paths, describe_type=describe_type,
            inference=inference,
        )
        return (
            GeneratedArrayType(
                _wrap(item_type, Nullability.DEFAULTED) if item_nullable else item_type
            ),
            declarations,
            not node.declared,
        )

    struct_name = f"{_path_prefix(paths)}{_class_part(_leaf_name(paths))}Struct"
    described = _struct_member_texts(describe_type)
    members: list[GeneratedField] = []
    nested: list[GeneratedClass] = []
    for child in node.children:
        field_, child_declarations = _tree_field(
            node=child, paths=paths.child(child.name),
            describe_type=_member_type(
                described, child, describe_type=describe_type, paths=paths,
            ),
            inference=inference,
        )
        members.append(field_)
        nested.extend(child_declarations)
    nested.append(GeneratedClass(struct_name, tuple(members), base="Struct"))
    return GeneratedStructType(struct_name), tuple(nested), not node.declared


def _member_type(
    described: dict[str, str], child: "_ParquetNode", *,
    describe_type: str, paths: _Paths,
) -> str:
    """The type one record member is reported as, by either authority.

    The flattened ``DESCRIBE`` string names the members it carries; a member it
    leaves out still has a type of its own in the footer. Nothing here may guess:
    a member no authority types would otherwise be read as text, which is a
    claim about a value nobody made.
    """
    reported = described.get(child.name) or child.duckdb_type
    if reported is None:
        raise GenerationError(
            f"member {paths.child(child.name).logical_text!r} is declared by the "
            f"Parquet footer, but {describe_type!r} names no type for it and the "
            "footer carries none either; the two views of this file do not agree "
            "about its shape"
        )
    return reported


def _item_type_text(describe_type: str, carrier: _ParquetNode, *, paths: _Paths) -> str:
    """The type one list item is reported as, by either authority.

    The flattened ``DESCRIBE`` string carries the item type inside its brackets
    when it carries an array at all; otherwise the repeated node's own type is the
    only report of it. A string naming neither is a disagreement, not an absence
    of type: inventing one here would put a claim about the item in the contract.
    """
    reported = _array_item_text(describe_type) or carrier.duckdb_type
    if reported is None:
        raise GenerationError(
            f"column {paths.logical_text!r} is a list in the Parquet footer, but "
            f"{describe_type!r} names no item type and the {carrier.name!r} node "
            "carries none either; the two views of this file do not agree about "
            "its shape"
        )
    return reported


def _item_of_list(
    *, wrapper: _ParquetNode, paths: _Paths, describe_type: str, inference: _Inference,
) -> tuple[GeneratedType, tuple[GeneratedClass, ...], bool]:
    """The item shape of a REPEATED wrapper, and whether that item is nullable.

    A legacy two-level list repeats a primitive directly; the standard
    three-level convention repeats a group named ``element``.
    """
    if not wrapper.children:
        item_paths = paths.child(wrapper.name)
        scalar = _resolve_scalar(
            _item_type_text(describe_type, wrapper, paths=paths),
            path=item_paths.logical_text,
        )
        return GeneratedScalarType(scalar), (), not wrapper.declared
    element = wrapper.children[0]
    item_paths = paths.child(wrapper.name, element.name)
    item_type, declarations, item_nullable = _shape_for_node(
        node=element, paths=item_paths,
        describe_type=_item_type_text(describe_type, element, paths=paths),
        inference=inference,
    )
    return item_type, declarations, item_nullable


def _leaf_name(paths: _Paths) -> str:
    """The field a derived record is named after.

    The Parquet three-level list convention names the item node ``element``, so a
    record inside an array would otherwise be named for the convention rather
    than for the field it belongs to.
    """
    parts = [part for part in paths.logical if part not in _LIST_WRAPPERS]
    return parts[-1] if parts else "Item"


def _path_prefix(paths: _Paths) -> str:
    """The derived-record prefix contributed by the members above this one.

    Keyed on the member path rather than the leaf name, so two unrelated structs
    may share a member name.
    """
    parts = [part for part in paths.logical if part not in _LIST_WRAPPERS]
    return "".join(_class_part(part) for part in parts[:-1])


def _tree_field(
    *, node: _ParquetNode, paths: _Paths, describe_type: str, inference: _Inference,
) -> tuple[GeneratedField, tuple[GeneratedClass, ...]]:
    """One member whose shape comes from the Parquet node tree."""
    shape, declarations, _shape_is_nullable = _shape_for_node(
        node=node, paths=paths, describe_type=describe_type, inference=inference,
    )
    value = _wrap(shape, _level_nullability(node.repetition))
    return (
        _make_field(node.name, paths, value, inference=inference),
        declarations,
    )


def _is_list_node(node: _ParquetNode) -> bool:
    return (
        bool(node.children) and len(node.children) <= 2
        and any(child.name in _LIST_WRAPPERS for child in node.children)
    )


def _level_nullability(repetition: str) -> Nullability:
    """The file's own word for one node: ``required`` is a claim, ``optional`` is not."""
    return Nullability.DECLARED if repetition.upper() == "REQUIRED" else Nullability.DEFAULTED


def _text_item_shape(
    *, type_name: str, parent_class: str, paths: _Paths, inference: _Inference,
) -> tuple[GeneratedType, tuple[GeneratedClass, ...]]:
    """Resolve the item shape carried by a flattened ``DESCRIBE`` type string.

    A flattened string names no nullability at any level, so nothing here may
    claim it: the result is a shape, and the caller decides nullability. An item
    has no name of its own in this form.
    """
    normalized = type_name.strip()
    item = _array_item_text(normalized)
    if item is not None:
        return _text_item_shape(
            type_name=item, parent_class=parent_class,
            paths=paths, inference=inference,
        )
    item_paths = paths.child("element") if paths.logical[-1] != "element" else paths
    if not _is_struct_text(normalized):
        scalar = _resolve_scalar(normalized, path=item_paths.logical_text)
        return GeneratedScalarType(scalar), ()
    struct_name = f"{parent_class}{_class_part(paths.logical[-1])}Struct"
    members: list[GeneratedField] = []
    nested: list[GeneratedClass] = []
    for member_name, member_type in _struct_member_texts(normalized).items():
        field_, declarations = _text_field(
            name=member_name, type_name=member_type, nullability=Nullability.DEFAULTED,
            parent_class=struct_name, paths=item_paths.child(member_name),
            inference=inference,
        )
        members.append(field_)
        nested.extend(declarations)
    nested.append(GeneratedClass(struct_name, tuple(members), base="Struct"))
    return GeneratedStructType(struct_name), tuple(nested)


def _text_field(
    *, name: str, type_name: str, nullability: Nullability, parent_class: str,
    paths: _Paths, inference: _Inference,
) -> tuple[GeneratedField, tuple[GeneratedClass, ...]]:
    """One member inferred from a ``DESCRIBE`` type string, nullability included."""
    normalized = type_name.strip()
    declarations: tuple[GeneratedClass, ...] = ()
    if _array_item_text(normalized) is not None:
        item, declarations = _text_item_shape(
            type_name=normalized, parent_class=parent_class, paths=paths,
            inference=inference,
        )
        # A flattened type string names no nullability at any level, so an item
        # of a schema-less array is nullable too: absence of a declaration is not
        # a declaration of presence, at the item level as much as the field's.
        if not isinstance(item, GeneratedNullableType):
            item = GeneratedNullableType(item)
        value: GeneratedType = GeneratedArrayType(item)
    elif _is_struct_text(normalized):
        struct_name = f"{parent_class}{_class_part(name)}Struct"
        members: list[GeneratedField] = []
        nested: list[GeneratedClass] = []
        for member_name, member_type in _struct_member_texts(normalized).items():
            field_, member_declarations = _text_field(
                name=member_name, type_name=member_type,
                nullability=Nullability.DEFAULTED, parent_class=struct_name,
                paths=paths.child(member_name), inference=inference,
            )
            members.append(field_)
            nested.extend(member_declarations)
        nested.append(GeneratedClass(struct_name, tuple(members), base="Struct"))
        value = GeneratedStructType(struct_name)
        declarations = tuple(nested)
    else:
        scalar = _resolve_scalar(
            normalized, path=paths.logical_text, column=_top_level_column(paths),
        )
        value = GeneratedScalarType(scalar)

    return (
        _make_field(
            name, paths, _wrap(value, nullability), inference=inference,
        ),
        declarations,
    )


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _remote_source(value: str) -> bool:
    """Whether ``value`` is a DuckDB-readable remote object URL."""
    return urlparse(value).scheme.lower() in _REMOTE_SCHEMES


def _source_suffix(value: str) -> str:
    """Return a source suffix without treating a URL query as part of its name."""
    return Path(urlparse(value).path if _remote_source(value) else value).suffix.lower()


def _source_stem(value: str) -> str:
    return Path(urlparse(value).path if _remote_source(value) else value).stem


def _source_label(source: str, sources: tuple[str, ...]) -> str:
    """How one physical source is named in a generated provenance header."""
    name = Path(urlparse(source).path if _remote_source(source) else source).name
    label = f"{name} ({_source_suffix(source).lstrip('.')})"
    if len(sources) > 1:
        return f"{label} and {len(sources) - 1} more file(s)"
    return label


def _nullability_note(
    tier: SchemaTier, source: str, sources: tuple[str, ...], relation: str,
    declarations: tuple[str, ...] = (),
) -> NullabilityNote:
    label = _source_label(source, sources)
    if tier == "enforced":
        line = (
            f"nullability: enforced by relation '{relation}' in {label} (NOT NULL)"
        )
    elif tier == "declared":
        line = f"nullability: declared by {label} (required/optional)"
    else:
        line = f"nullability: not declared by {label} - all members nullable"
    return NullabilityNote(line, tuple(sources), declarations)


def _load_remote_access(connection: duckdb.DuckDBPyConnection, source: str) -> None:
    """Enable DuckDB's URL and S3 filesystem support when a remote input needs it."""
    if not _remote_source(source):
        return
    try:
        connection.execute("LOAD httpfs")
    except duckdb.Error:
        try:
            connection.execute("INSTALL httpfs")
            connection.execute("LOAD httpfs")
        except duckdb.Error as error:
            raise GenerationError(
                f"cannot enable DuckDB httpfs support required for remote source {source!r}: {error}"
            ) from error


@dataclass(frozen=True)
class _LogicalTable:
    group_path: tuple[str, ...]
    name: str
    sources: tuple[str, ...]
    hive_partitioned: bool = False


def _filesystem_source(filesystem: AbstractFileSystem, path: str) -> str:
    value = filesystem.unstrip_protocol(path)
    if isinstance(value, str) and value.startswith("file://"):
        return str(Path(value[7:]).resolve())
    return str(value)


def _logical_tables(
    source: str,
    request_id: str,
    layout: Literal["files", "parquet_parts", "hive_partitioned_parquet"],
    *,
    anonymous: bool = False,
) -> tuple[_LogicalTable, ...]:
    """Walk a filesystem and collapse partitions/parts into logical datasets."""
    storage_options = {"anon": True} if urlparse(source).scheme.lower() == "s3" and anonymous else {}
    filesystem, root = fsspec.core.url_to_fs(source, **storage_options)
    if filesystem.isfile(root):
        return (_LogicalTable((), _source_stem(source), (source,)),)
    if not filesystem.isdir(root):
        raise GenerationError(f"data-contract inference input does not exist: {source}")

    root_path = PurePosixPath(str(root).replace("\\", "/").rstrip("/"))
    grouped: dict[tuple[tuple[str, ...], str], list[tuple[str, bool]]] = {}
    for raw_path in sorted(filesystem.find(root)):
        if not filesystem.isfile(raw_path):
            continue
        path = PurePosixPath(str(raw_path).replace("\\", "/"))
        suffix = path.suffix.lower()
        if suffix not in _DATA_SUFFIXES:
            continue
        if layout != "files" and suffix not in {".parquet", ".pq"}:
            continue
        try:
            relative = path.relative_to(root_path)
        except ValueError as error:
            raise GenerationError(f"filesystem returned a path outside the inference root: {raw_path}") from error
        parents = relative.parts[:-1]
        partitioned = layout == "hive_partitioned_parquet" and any(
            _HIVE_PARTITION.fullmatch(part) for part in parents
        )
        logical_parents = tuple(
            part for part in parents
            if layout != "hive_partitioned_parquet" or not _HIVE_PARTITION.fullmatch(part)
        )
        if layout != "files":
            if logical_parents:
                group_path, table_name = logical_parents[:-1], logical_parents[-1]
            else:
                group_path, table_name = (), request_id
        else:
            group_path, table_name = logical_parents, path.stem
        grouped.setdefault((group_path, table_name), []).append(
            (_filesystem_source(filesystem, str(raw_path)), partitioned)
        )
    if not grouped:
        raise GenerationError(f"data input {source} contains no supported relations")
    return tuple(
        _LogicalTable(group_path, name, tuple(item[0] for item in files), any(item[1] for item in files))
        for (group_path, name), files in sorted(grouped.items())
    )


class DataContractInferenceConfig(ProviderGenerationConfig):
    source: str
    relation: str | None = None
    mode: Literal["table", "table_group"] = "table"
    layout: Literal["files", "parquet_parts", "hive_partitioned_parquet"] = "files"
    anonymous: bool = False
    #: The canonical type an author means a TOP-LEVEL column to hold, whatever the
    #: reader reports for it, keyed by column name. A sniffing reader leaves a
    #: ``YYYY-MM-DDTHH:MM`` string as ``VARCHAR``, so the temporal type of such a
    #: feed has to be declared rather than inferred; the contract carries the
    #: declared type and the source view applies the checked cast to it.
    promote: dict[str, str] = {}


class InferDataContractProvider(Provider[DataContractInferenceConfig]):
    """Infer portable table or table-group declarations from a data input."""

    ID: ClassVar[str] = "infer_data_contract"
    VERSION: ClassVar[str] = "3"
    CONFIG_TYPE: ClassVar[type[ProviderGenerationConfig]] = DataContractInferenceConfig

    @classmethod
    async def dependencies(cls, context: ProviderContext[DataContractInferenceConfig]) -> tuple[Path, ...]:
        return await asyncio.to_thread(cls._dependencies, context)

    @classmethod
    def _dependencies(cls, context: ProviderContext[DataContractInferenceConfig]) -> tuple[Path, ...]:
        if _remote_source(context.config.source):
            return ()
        source = context.resolve_path(context.config.source)
        if source.is_dir():
            return tuple(
                path for path in sorted(source.rglob("*"), key=lambda item: item.as_posix())
                if path.is_file() and path.suffix.lower() in {
                    ".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".parquet", ".pq",
                }
            )
        return (source,)

    @classmethod
    def _relations(cls, connection: duckdb.DuckDBPyConnection, source: str) -> tuple[str, ...]:
        if _source_suffix(source) not in _DATABASE_SUFFIXES:
            return (_source_stem(source),)
        rows = connection.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema NOT IN ('information_schema', 'pg_catalog') ORDER BY table_name"
        ).fetchall()
        return tuple(str(row[0]) for row in rows)

    @classmethod
    def _describe(
        cls, connection: duckdb.DuckDBPyConnection, sources: tuple[str, ...], relation: str,
        *, hive_partitioned: bool = False,
    ) -> tuple[tuple[str, str, Nullability], ...]:
        """Structure and tier-decided nullability for one relation's columns.

        ``DESCRIBE`` is the structural boundary — it decides which columns exist
        and what scalar each holds. Its ``null`` column reports only *enforced*
        catalog constraints, so it is silent about what a file declares, and
        nullability is therefore decided by tier rather than read off it directly.
        Nullability is never derived from observed values.
        """
        source = sources[0]
        suffix = _source_suffix(source)
        if suffix in _DATABASE_SUFFIXES:
            query = f"SELECT * FROM {_quote_identifier(relation)}"
            parameters: list[Any] = []
        elif suffix in _PARQUET_SUFFIXES:
            query = (
                "SELECT * FROM read_parquet(?, hive_partitioning = true)"
                if hive_partitioned else "SELECT * FROM read_parquet(?)"
            )
            parameters = [source if len(sources) == 1 else list(sources)]
        elif suffix in {".csv", ".tsv"}:
            query, parameters = "SELECT * FROM read_csv_auto(?)", [source if len(sources) == 1 else list(sources)]
        elif suffix in {".json", ".jsonl", ".ndjson"}:
            query, parameters = "SELECT * FROM read_json_auto(?)", [source if len(sources) == 1 else list(sources)]
        else:
            raise GenerationError(
                f"unsupported data-contract inference input format {suffix or '<none>'!r}"
            )
        try:
            rows = connection.execute(f"DESCRIBE {query}", parameters).fetchall()
        except duckdb.Error as error:
            raise GenerationError(
                f"cannot infer schema for {source} relation {relation!r}: {error}"
            ) from error
        tier = _tier_for_suffix(suffix)
        return tuple(
            (
                str(row[0]), str(row[1]),
                _describe_nullability(tier, str(row[2]).upper() != "NO"),
            )
            for row in rows
        )

    @classmethod
    def _members(
        cls,
        *,
        connection: duckdb.DuckDBPyConnection,
        described: tuple[tuple[str, str, Nullability], ...],
        sources: tuple[str, ...],
        class_prefix: str,
        inference: _Inference,
    ) -> tuple[tuple[GeneratedField, tuple[GeneratedClass, ...]], ...]:
        """One finished member per DuckDB column, with the source's own shape.

        The two authorities stay separate: DuckDB's own read decides which columns
        exist and what scalar each holds, and — for Parquet only —
        ``parquet_schema()`` decides nested structure and nullability at every
        level. A DuckDB column that no file declares, such as a hive partition
        key, is ``DEFAULTED``; a node the read does not expose means the two views
        of the file disagree, which fails.

        Where the request declares a canonical type for one of these columns, the
        declaration replaces the type the read reported before either authority is
        read for shape: it is the author's own word about what the column means, and
        the scan's checked cast is what tests it against the values.
        """
        suffix = _source_suffix(sources[0])
        nodes = _parquet_trees(connection, sources) if suffix in _PARQUET_SUFFIXES else ()
        by_column = {node.name: node for node in nodes}
        unbacked = sorted(set(by_column) - {name for name, _type, _null in described})
        if unbacked:
            raise GenerationError(
                "parquet_schema() declares "
                + ", ".join(repr(name) for name in unbacked)
                + f" of {sources[0]!r}, which DuckDB's read of the same file does not expose"
            )
        members: list[tuple[GeneratedField, tuple[GeneratedClass, ...]]] = []
        for name, type_name, nullability in described:
            node = by_column.get(name)
            paths = _Paths((name,), (name,))
            declared = inference.promote.get(name)
            if declared is not None:
                inference.promoted.add(name)
                if node is not None and node.children:
                    raise _container_promotion(type_name, column=name, canonical=declared)
                type_name = _promoted_type_name(
                    type_name, column=name, canonical=declared,
                )
            if node is None:
                members.append(_text_field(
                    name=name, type_name=type_name, nullability=nullability,
                    parent_class=class_prefix, paths=paths, inference=inference,
                ))
                continue
            members.append(_tree_field(
                node=node, paths=paths, describe_type=type_name, inference=inference,
            ))
        return tuple(members)

    @classmethod
    def _table_classes(
        cls, *, connection: duckdb.DuckDBPyConnection, sources: tuple[str, ...],
        relation: str, class_name: str, final: bool, hive_partitioned: bool = False,
        inference: _Inference,
    ) -> tuple[GeneratedClass, ...]:
        fields: list[GeneratedField] = []
        supporting: list[GeneratedClass] = []
        inference.used_names = {}
        described_fields = cls._describe(
            connection, sources, relation, hive_partitioned=hive_partitioned,
        )
        try:
            for field_, nested in cls._members(
                connection=connection, described=described_fields, sources=sources,
                class_prefix=class_name, inference=inference,
            ):
                previous = inference.used_names.get(field_.python_name)
                if previous is not None:
                    raise GenerationError(
                        f"columns {previous!r} and {field_.external_name!r} "
                        f"collide as {field_.python_name!r}"
                    )
                inference.used_names[field_.python_name] = field_.external_name
                fields.append(field_)
                supporting.extend(nested)
            if not fields:
                raise GenerationError(f"relation {relation!r} has no columns")
            inference.columns[relation] = {field.external_name for field in fields}
        except GenerationError as error:
            resource = sources[0]
            additional = (
                f" and {len(sources) - 1} additional resources"
                if len(sources) > 1 else ""
            )
            raise GenerationError(
                f"cannot generate data contract for resource {resource!r}{additional} "
                f"relation {relation!r}: {error}"
            ) from error
        return (
            *supporting,
            GeneratedClass(
                class_name,
                tuple(fields),
                base="Table" if final else None,
                declaration_name=relation if final else None,
            ),
        )

    @classmethod
    def _table_group_package(
        cls, context: ProviderContext[DataContractInferenceConfig],
        tables: tuple[_LogicalTable, ...], connection: duckdb.DuckDBPyConnection,
        inference: _Inference,
    ) -> GeneratedPackage:
        files: list[GeneratedFile] = []
        notes: dict[str, NullabilityNote] = {}
        group_paths = {
            prefix for table in tables
            for size in range(len(table.group_path) + 1)
            for prefix in (table.group_path[:size],)
        }

        def group_class(path: tuple[str, ...]) -> str:
            return f"{''.join(_class_part(part) for part in path) or _class_part(context.request_id)}TableGroup"

        for table in tables:
            table_name = f"{_class_part(table.name)}Table"
            classes = cls._table_classes(
                connection=connection,
                sources=table.sources,
                relation=table.name,
                class_name=table_name,
                final=True,
                hive_partitioned=table.hive_partitioned,
                inference=inference,
            )
            cls._report_null_statistics(connection, table.sources, inference)
            note = _nullability_note(
                _tier_for_suffix(_source_suffix(table.sources[0])),
                table.sources[0], table.sources, table.name, (table_name,),
            )
            notes.setdefault(note.line, note)
            relative = Path(*table.group_path) / f"{_identifier(table.name, fallback='table')}.py"
            files.append(GeneratedFile(relative, classes, (table_name,)))

        for group_path in sorted(group_paths, key=lambda value: (-len(value), value)):
            members = [
                GeneratedMember(
                    _identifier(table.name, fallback="table"),
                    f"{_class_part(table.name)}Table",
                )
                for table in tables if table.group_path == group_path
            ]
            children = sorted({
                path[len(group_path)] for path in group_paths
                if len(path) == len(group_path) + 1
                and path[:len(group_path)] == group_path
            })
            members.extend(
                GeneratedMember(_identifier(child, fallback="group"), group_class((*group_path, child)))
                for child in children
            )
            logical_name = group_path[-1] if group_path else context.request_id
            declaration = GeneratedClass(
                group_class(group_path),
                members=tuple(members),
                base="TableGroup",
                declaration_name=logical_name,
            )
            files.append(GeneratedFile(Path(*group_path) / "__init__.py", (declaration,), (declaration.name,)))
        return GeneratedPackage(tuple(files), tuple(notes.values()))

    @classmethod
    def _report_null_statistics(
        cls, connection: duckdb.DuckDBPyConnection, sources: tuple[str, ...],
        inference: _Inference,
    ) -> None:
        """Test declared non-nullability against the file's own column statistics.

        A statistic tests a claim, it never sets or enforces one, so this reports
        and never fails. Generation is where it earns most: the author can still
        change the request. An absent statistic is unknown and is never read as a
        zero count.
        """
        if _source_suffix(sources[0]) not in _PARQUET_SUFFIXES or not inference.declared_paths:
            return
        report = read_declared_null_statistics(
            _reader(connection), sources, sorted(inference.declared_paths),
        )
        for statistic in report.violations:
            _LOGGER.warning(
                "%s reports %d null value(s) in %d rows for the declared non-null "
                "column %r; inference will keep claiming it is non-null until the "
                "request says otherwise, and the build guard will abort on it",
                _source_label(sources[0], sources), statistic.nulls, statistic.values,
                statistic.schema_path,
            )
        for path in report.unknown_paths:
            _LOGGER.debug("no null statistics published for %r; unknown is not zero", path)

    @classmethod
    async def generate(
        cls, context: ProviderContext[DataContractInferenceConfig],
    ) -> GeneratedPackage:
        return await asyncio.to_thread(cls._generate, context)

    @classmethod
    def _generate(
        cls, context: ProviderContext[DataContractInferenceConfig],
    ) -> GeneratedPackage:
        remote = _remote_source(context.config.source)
        path = None if remote else context.resolve_path(context.config.source)
        source = context.config.source if remote else str(path)
        if context.config.layout != "files" and context.config.mode != "table_group":
            raise GenerationError(f"layout={context.config.layout!r} requires mode='table_group'")
        if _source_suffix(source) in _DATABASE_SUFFIXES:
            raise GenerationError(
                f"data-contract inference input {source} is a DuckDB database: its "
                "relations can be inferred but never bound, because no InputFormat "
                "selects a database reader. Export the relation to Parquet, or "
                "declare the contract outside a generated package."
            )
        inference = _Inference(promote=_declared_promotions(context.config.promote))
        if context.config.mode == "table_group":
            if context.config.relation is not None:
                raise GenerationError("table-group inference does not accept relation=")
            tables = _logical_tables(
                source,
                context.request_id,
                context.config.layout,
                anonymous=context.config.anonymous,
            )
            connection = duckdb.connect(":memory:")
            try:
                for table in tables:
                    for item in table.sources:
                        _load_remote_access(connection, item)
                package = cls._table_group_package(context, tables, connection, inference)
                _require_promoted_columns(inference)
                return package
            finally:
                connection.close()
        if path is not None and not path.exists():
            raise GenerationError(f"data-contract inference input does not exist: {path}")
        if path is not None and path.is_dir():
            raise GenerationError("directory inference requires mode='table_group'")
        connection = duckdb.connect(":memory:")
        try:
            _load_remote_access(connection, source)
            relations = cls._relations(connection, source)
            if not relations:
                raise GenerationError(f"data input {path} exposes no relations")
            if context.config.relation is None and len(relations) != 1:
                raise GenerationError(
                    "table-contract inference requires relation= when the input "
                    "exposes multiple relations"
                )
            relation = context.config.relation or relations[0]
            if relation not in relations:
                raise GenerationError(f"data input {path} has no relation {relation!r}")
            class_name = f"{_class_part(context.request_id)}Table"
            classes = cls._table_classes(
                connection=connection, sources=(source,), relation=relation,
                class_name=class_name, final=True, inference=inference,
            )
            cls._report_null_statistics(connection, (source,), inference)
            _require_promoted_columns(inference)
            return GeneratedPackage(
                (GeneratedFile(Path("__init__.py"), classes, (class_name,)),),
                (_nullability_note(
                    _tier_for_suffix(_source_suffix(source)), source, (source,), relation,
                ),),
            )
        finally:
            connection.close()

__all__ = ["DataContractInferenceConfig", "InferDataContractProvider"]
