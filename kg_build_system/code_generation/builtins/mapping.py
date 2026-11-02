"""The DuckDB-to-canonical digest gate used by inference.

This is the mapping an inference provider needs to decide whether a reported
physical type is usable, needs an author declaration, or has no canonical
meaning. It is local to generation because the execution engine is a separate
package; the two tables state the same gate.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Final, Literal

from ...types.interfaces import UnitTypeName, is_canonical_unit_name

ARRAY_CANONICAL: Final = "array"
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
    """A DuckDB type digestible only through a declared override."""

    disposition: Literal["declared_only"]
    canonical: CanonicalTypeName
    narrowing: str


@dataclass(frozen=True, slots=True)
class RefusedDigest:
    """A DuckDB type with no meaning-preserving canonical type yet."""

    disposition: Literal["refused"]
    reason: str


type TypeDigest = CanonicalDigest | DeclaredOnlyDigest | RefusedDigest


def _canonical(name: CanonicalTypeName) -> CanonicalDigest:
    return CanonicalDigest("canonical", name)


def _declared(name: CanonicalTypeName, narrowing: str) -> DeclaredOnlyDigest:
    return DeclaredOnlyDigest("declared_only", name, narrowing)


def _refused(reason: str) -> RefusedDigest:
    return RefusedDigest("refused", reason)


DIGEST_TABLE: Final[dict[str, TypeDigest]] = {
    "BOOLEAN": _canonical("bool"),
    "TINYINT": _canonical("int"),
    "SMALLINT": _canonical("int"),
    "INTEGER": _canonical("int"),
    "BIGINT": _canonical("int"),
    "UTINYINT": _canonical("int"),
    "USMALLINT": _canonical("int"),
    "UINTEGER": _canonical("int"),
    "UBIGINT": _declared(
        "int",
        "values above 2^63-1 have no signed 64-bit equivalent and the checked cast aborts rather than wrapping",
    ),
    "HUGEINT": _declared(
        "int",
        "128-bit values outside the signed 64-bit range abort the checked cast, and without it a HUGEINT property degrades to DOUBLE on Parquet export",
    ),
    "UHUGEINT": _declared(
        "int",
        "unsigned 128-bit values outside the signed 64-bit range abort the checked cast",
    ),
    "FLOAT": _canonical("float"),
    "DOUBLE": _canonical("float"),
    "VARCHAR": _canonical("str"),
    "ENUM": _canonical("str"),
    "UUID": _canonical("uuid"),
    "DATE": _canonical("date"),
    "TIME": _canonical("time"),
    "TIME_NS": _declared(
        "time",
        "the cast rounds nanoseconds silently: 10:00:00.123456789 becomes 10:00:00.123457",
    ),
    "TIMESTAMP": _canonical("timestamp"),
    "TIMESTAMP_S": _canonical("timestamp"),
    "TIMESTAMP_MS": _canonical("timestamp"),
    "TIMESTAMP_NS": _declared(
        "timestamp",
        "the cast drops nanoseconds silently: 2026-01-01 10:00:00.123456789 becomes 2026-01-01 10:00:00.123456",
    ),
    "LIST": _canonical(ARRAY_CANONICAL),
    "ARRAY": _canonical(ARRAY_CANONICAL),
    "STRUCT": _canonical(STRUCT_CANONICAL),
    "DECIMAL": _refused(
        "exact numeric needs a parameterised canonical type plus DuckDB's result-width rules, and DECIMAL division returns DOUBLE, so no division operator could be offered for it"
    ),
    "BIGNUM": _refused(
        "it is an unbounded integer: decimal is bounded and str would change its meaning, and the client hands it over as text"
    ),
    "BIT": _refused(
        "a bit string is rare; a str canonical would be cheap to add but changes its meaning"
    ),
    "BLOB": _refused(
        "binary has no total order, so the core operators cannot merge or deduplicate it"
    ),
    "TIME WITH TIME ZONE": _refused("no canonical type has been chosen for a zoned time of day"),
    "TIMESTAMP WITH TIME ZONE": _refused(
        "an instant and a local date-time are different types, and the fetched object takes its tzinfo from the session TimeZone setting rather than from the data, so materialising an instant is machine-dependent until that setting is pinned"
    ),
    "INTERVAL": _refused("calendar-aware months mean an interval is not a duration value"),
    "MAP": _refused(
        "a mapping is digestible through the entries representation, but the nested-shape work is deferred"
    ),
    "UNION": _refused(
        "a tagged sum has no framework analogue and the client drops the tag"
    ),
    "VARIANT": _refused(
        "per-row self-describing typing has no canonical form and the client drops it"
    ),
    "ROW": _refused("an anonymous record has no field names to declare"),
    "NULL": _refused(
        "an untyped NULL column is an absent declaration; DESCRIBE reports INTEGER for it"
    ),
    "TYPE": _refused("TYPE is an internal pseudo-type"),
    "GEOMETRY": _refused(
        "geometry is extension-conditional, so a definition using it is not portable"
    ),
    "GEOGRAPHY": _refused(
        "geography is extension-conditional, so a definition using it is not portable"
    ),
}

TYPE_NAME_ALIASES: Final[dict[str, str]] = {
    "JSON": "VARCHAR",
    "TIMETZ": "TIME WITH TIME ZONE",
    "TIMESTAMPTZ": "TIMESTAMP WITH TIME ZONE",
}

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

_PARAMETER_LIST = re.compile(r"\s*\(.*\)$")


def canonical_type_name(value: str) -> str:
    """One DuckDB type name as the gate keys it: parameters removed, upper case."""
    return _PARAMETER_LIST.sub("", value.strip()).upper()


def digest_for(value: str) -> TypeDigest | None:
    """The gate's decision for one DuckDB type name, or ``None`` when unknown."""
    name = canonical_type_name(value)
    digest = DIGEST_TABLE.get(name)
    if digest is not None:
        return digest
    target = TYPE_NAME_ALIASES.get(name)
    return DIGEST_TABLE.get(target) if target is not None else None


def canonical_sql_type(canonical: UnitTypeName) -> str:
    """The SQL type one canonical unit type is written as."""
    if not is_canonical_unit_name(canonical):
        raise ValueError(f"canonical {canonical!r} has no SQL type of its own")
    return CANONICAL_SQL_TYPES[canonical]


__all__ = [
    "ARRAY_CANONICAL", "CANONICAL_SQL_TYPES", "DIGEST_TABLE", "STRUCT_CANONICAL",
    "TYPE_NAME_ALIASES", "CanonicalDigest", "CanonicalTypeName",
    "DeclaredOnlyDigest", "DigestDisposition", "RefusedDigest", "TypeDigest",
    "canonical_sql_type", "canonical_type_name", "digest_for",
]
