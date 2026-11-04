"""The DuckDB-to-canonical digest gate, as data.

This module is ``DUCKDB_TYPE_ACCEPTANCE_MATRIX.md`` expressed as data rather than
prose: every DuckDB type tag is classified exactly once, together with the fact
that made the matrix classify it that way. The gate has three dispositions:

``canonical``
    The type digests as it stands, or through the widening cast the source view
    applies automatically. It carries the canonical logical type it maps to.
``declared_only``
    The only cast that reaches a canonical type *narrows* the value, so the
    digest needs an author declaration before it may proceed. It carries the
    target canonical type and the measured behaviour of that narrowing.
``refused``
    No meaning-preserving canonical type exists yet. It carries the reason.

Being unusable as a graph property is never a refusal: a transformation converts
rather than refuses. Refusal means no canonical form exists at all.

The table is validated against the live engine by
``tests/test_duckdb_type_digest.py``, which asserts every canonical tag of
``duckdb_types()`` is classified exactly once and that no key here is
unreachable, so a DuckDB upgrade that adds or renames a type fails a test
instead of leaving this table stale. An engine is a leaf layer: nothing here
imports the edit-time or build-time subsystems that read this table.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Final, Literal

from kg_build_system.kernel.model.public.types import (
    UnitTypeName,
    is_canonical_unit_name,
)

__all__ = [
    "ARRAY_CANONICAL",
    "CANONICAL_SQL_TYPES",
    "DIGEST_TABLE",
    "EXTENSION_CONDITIONAL_TYPE_NAMES",
    "STRUCT_CANONICAL",
    "TYPE_NAME_ALIASES",
    "ArraySqlType",
    "CanonicalDigest",
    "DeclaredOnlyDigest",
    "RefusedDigest",
    "CanonicalTypeName",
    "DigestDisposition",
    "SqlType",
    "StructSqlType",
    "TypeDigest",
    "canonical_sql_type",
    "canonical_type_name",
    "digest_for",
]

#: The canonical name of the ordered-collection shape. Lowercase like a canonical
#: unit name; a container composes its SQL type from its item type.
ARRAY_CANONICAL: Final = "array"

#: The canonical name of the nested-record shape, composed from its members.
STRUCT_CANONICAL: Final = "struct"

type CanonicalTypeName = UnitTypeName | Literal["array", "struct"]
type DigestDisposition = Literal["canonical", "declared_only", "refused"]


@dataclass(frozen=True, slots=True)
class CanonicalDigest:
    """A DuckDB type the gate digests as-is or by a widening cast."""

    disposition: Literal["canonical"]
    canonical: CanonicalTypeName


@dataclass(frozen=True, slots=True)
class DeclaredOnlyDigest:
    """A DuckDB type digestible only through a declared override.

    ``narrowing`` is what the matrix measured the normalising cast to do to the
    value, which is the whole reason the author has to ask for it.
    """

    disposition: Literal["declared_only"]
    canonical: CanonicalTypeName
    narrowing: str


@dataclass(frozen=True, slots=True)
class RefusedDigest:
    """A DuckDB type with no meaning-preserving canonical type yet."""

    disposition: Literal["refused"]
    reason: str


type TypeDigest = CanonicalDigest | DeclaredOnlyDigest | RefusedDigest


def canonical_digest(name: CanonicalTypeName) -> CanonicalDigest:
    return CanonicalDigest("canonical", name)


def declared_only_digest(name: CanonicalTypeName, narrowing: str) -> DeclaredOnlyDigest:
    return DeclaredOnlyDigest("declared_only", name, narrowing)


def refused_digest(reason: str) -> RefusedDigest:
    return RefusedDigest("refused", reason)


#: Every DuckDB type name the digest gate knows, keyed on the name DuckDB itself
#: reports for it — the ``logical_type`` column of ``duckdb_types()``, which is
#: also what ``DESCRIBE`` and ``parquet_schema()`` print once their parameters are
#: removed (see ``canonical_type_name``).
DIGEST_TABLE: Final[dict[str, TypeDigest]] = {
    # Signed and unsigned integers of every width widen to BIGINT without losing
    # a value; DuckDB arithmetic stays at the operand width, so the widening costs
    # a column nothing it had and gives it room the canonical type needs.
    "BOOLEAN": canonical_digest("bool"),
    "TINYINT": canonical_digest("int"),
    "SMALLINT": canonical_digest("int"),
    "INTEGER": canonical_digest("int"),
    "BIGINT": canonical_digest("int"),
    "UTINYINT": canonical_digest("int"),
    "USMALLINT": canonical_digest("int"),
    "UINTEGER": canonical_digest("int"),
    # The wide integers reach int only through a checked cast to BIGINT, so they
    # are digestible only when an author declares that the values fit.
    "UBIGINT": declared_only_digest(
        "int",
        "values above 2^63-1 have no signed 64-bit equivalent and the checked "
        "cast aborts rather than wrapping",
    ),
    "HUGEINT": declared_only_digest(
        "int",
        "128-bit values outside the signed 64-bit range abort the checked cast, "
        "and without it a HUGEINT property degrades to DOUBLE on Parquet export",
    ),
    "UHUGEINT": declared_only_digest(
        "int",
        "unsigned 128-bit values outside the signed 64-bit range abort the "
        "checked cast",
    ),
    # Widening FLOAT to DOUBLE fixes the arithmetic width only: the stored value
    # is already single precision.
    "FLOAT": canonical_digest("float"),
    "DOUBLE": canonical_digest("float"),
    # JSON is a VARCHAR spelling and an ENUM's permitted labels are metadata about
    # the field rather than part of its type, so both digest as str.
    "VARCHAR": canonical_digest("str"),
    "ENUM": canonical_digest("str"),
    # A UUID is an identifier that merely has a canonical text form; the client
    # already carries it as uuid.UUID with no cast and no conversion.
    "UUID": canonical_digest("uuid"),
    "DATE": canonical_digest("date"),
    "TIME": canonical_digest("time"),
    # Nanosecond precision has nowhere to go: a Python time or datetime holds
    # microseconds, so both _NS types narrow silently and only a declaration may
    # ask for that.
    "TIME_NS": declared_only_digest(
        "time",
        "the cast rounds nanoseconds silently: 10:00:00.123456789 becomes "
        "10:00:00.123457",
    ),
    "TIMESTAMP": canonical_digest("timestamp"),
    "TIMESTAMP_S": canonical_digest("timestamp"),
    "TIMESTAMP_MS": canonical_digest("timestamp"),
    "TIMESTAMP_NS": declared_only_digest(
        "timestamp",
        "the cast drops nanoseconds silently: 2026-01-01 10:00:00.123456789 "
        "becomes 2026-01-01 10:00:00.123456",
    ),
    # Containers digest to the canonical composite shapes, composed from the item
    # or member types rather than from this name; a fixed-size array widens to a
    # list, which also removes the tuple the client hands fixed arrays over as.
    "LIST": canonical_digest(ARRAY_CANONICAL),
    "ARRAY": canonical_digest(ARRAY_CANONICAL),
    "STRUCT": canonical_digest(STRUCT_CANONICAL),
    # Everything below has no meaning-preserving canonical type yet.
    "DECIMAL": refused_digest(
        "exact numeric needs a parameterised canonical type plus DuckDB's "
        "result-width rules, and DECIMAL division returns DOUBLE, so no division "
        "operator could be offered for it"
    ),
    "BIGNUM": refused_digest(
        "it is an unbounded integer: decimal is bounded and str would change its "
        "meaning, and the client hands it over as text"
    ),
    "BIT": refused_digest(
        "a bit string is rare; a str canonical would be cheap to add but changes "
        "its meaning"
    ),
    "BLOB": refused_digest(
        "binary has no total order, so the core operators cannot merge or "
        "deduplicate it"
    ),
    "TIME WITH TIME ZONE": refused_digest(
        "no canonical type has been chosen for a zoned time of day"
    ),
    "TIMESTAMP WITH TIME ZONE": refused_digest(
        "an instant and a local date-time are different types, and the fetched "
        "object takes its tzinfo from the session TimeZone setting rather than "
        "from the data, so materialising an instant is machine-dependent until "
        "that setting is pinned"
    ),
    "INTERVAL": refused_digest(
        "calendar-aware months mean an interval is not a duration value"
    ),
    "MAP": refused_digest(
        "a mapping is digestible through the entries representation, but the "
        "nested-shape work is deferred"
    ),
    "UNION": refused_digest(
        "a tagged sum has no framework analogue and the client drops the tag"
    ),
    "VARIANT": refused_digest(
        "per-row self-describing typing has no canonical form and the client "
        "drops it"
    ),
    "ROW": refused_digest("an anonymous record has no field names to declare"),
    "NULL": refused_digest(
        "an untyped NULL column is an absent declaration; DESCRIBE reports "
        "INTEGER for it"
    ),
    "TYPE": refused_digest("TYPE is an internal pseudo-type"),
    "GEOMETRY": refused_digest(
        "geometry is extension-conditional, so a definition using it is not portable"
    ),
    "GEOGRAPHY": refused_digest(
        "geography is extension-conditional, so a definition using it is not portable"
    ),
}

#: Spellings DuckDB accepts for a type it reports under another name. Resolved to
#: the key above, so both the alias and the reported name digest identically.
TYPE_NAME_ALIASES: Final[dict[str, str]] = {
    "JSON": "VARCHAR",
    "TIMETZ": "TIME WITH TIME ZONE",
    "TIMESTAMPTZ": "TIMESTAMP WITH TIME ZONE",
}

#: Names DuckDB lists only while an extension provides them, so they are absent
#: from ``duckdb_types()`` on a machine that has not loaded one. They stay in the
#: table because a definition that uses one is still a definition to refuse.
EXTENSION_CONDITIONAL_TYPE_NAMES: Final = frozenset({"GEOGRAPHY"})

#: The SQL type the source view casts each canonical unit type to, per plan
#: section 5. A container composes its SQL type from its item or member types.
CANONICAL_SQL_TYPES: Final[dict[UnitTypeName, str]] = {
    "bool": "BOOLEAN",
    "int": "BIGINT",
    "float": "DOUBLE",
    "str": "VARCHAR",
    "date": "DATE",
    "time": "TIME",
    "timestamp": "TIMESTAMP",
    "uuid": "UUID",
}


@dataclass(frozen=True, slots=True)
class ArraySqlType:
    """An ordered collection whose SQL type is composed from one item type."""

    item: "SqlType"


@dataclass(frozen=True, slots=True)
class StructSqlType:
    """A nested record whose SQL type is composed from its members, in order.

    SQL types carry no nullability, so a member is a name and a type and nothing
    else; a member name is quoted as it is written unless it needs no quotes.
    """

    members: tuple[tuple[str, "SqlType"], ...]


#: A canonical type as SQL is written from it: a canonical unit name, or one of
#: the two container shapes composed from the types below it.
type SqlType = CanonicalTypeName | ArraySqlType | StructSqlType

_SIMPLE_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")

_PARAMETER_LIST = re.compile(r"\s*\(.*\)$")


def canonical_type_name(value: str) -> str:
    """One DuckDB type name as this table keys it: parameters removed, upper case.

    ``DECIMAL(18,2)``, ``ENUM('a', 'b')``, ``MAP(INTEGER, VARCHAR)`` and
    ``STRUCT(a INTEGER)`` are all reported with a parameter list the gate keys on
    the family alone.

    Example:
        ```python
        assert canonical_type_name("DECIMAL(18, 2)") == "DECIMAL"
        ```
    """
    return _PARAMETER_LIST.sub("", value.strip()).upper()


def digest_for(value: str) -> TypeDigest | None:
    """The digest gate's decision for one DuckDB type name, or ``None``.

    ``None`` means the name is not a DuckDB type this table has ever heard of,
    which is a different answer from a refusal and is reported separately.

    Example:
        ```python
        digest = digest_for("BIGINT")
        assert digest is not None
        ```
    """
    name = canonical_type_name(value)
    digest = DIGEST_TABLE.get(name)
    if digest is not None:
        return digest
    target = TYPE_NAME_ALIASES.get(name)
    return DIGEST_TABLE.get(target) if target is not None else None


def canonical_sql_type(canonical: SqlType) -> str:
    """The SQL a canonical type is written as, composed from its parts.

    A canonical unit type has one SQL type of its own — ``CANONICAL_SQL_TYPES``,
    plan section 5 — and a container composes its SQL from its item or member
    types, so ``Array[int]`` is ``BIGINT[]`` and ``Struct{a: int}`` is
    ``STRUCT(a BIGINT)``. A bare container name has no parts to compose from and
    is the one thing this function refuses.

    Example:
        ```python
        assert canonical_sql_type(ArraySqlType("int")) == "BIGINT[]"
        ```
    """
    if isinstance(canonical, ArraySqlType):
        return f"{canonical_sql_type(canonical.item)}[]"
    if isinstance(canonical, StructSqlType):
        if not canonical.members:
            raise ValueError("a struct SQL type composes its SQL from its members")
        return "STRUCT({})".format(", ".join(
            f"{sql_identifier(name)} {canonical_sql_type(member)}"
            for name, member in canonical.members
        ))
    if not is_canonical_unit_name(canonical):
        raise ValueError(
            f"canonical {canonical!r} composes its SQL type from its item or "
            "member types; only a canonical unit type has one of its own"
        )
    return CANONICAL_SQL_TYPES[canonical]


def sql_identifier(value: str) -> str:
    """A struct member name as SQL: quoted only where it has to be."""
    if _SIMPLE_IDENTIFIER.fullmatch(value):
        return value
    return '"' + value.replace('"', '""') + '"'
