"""Author declarations that replace a reader's view of one column."""
from __future__ import annotations

from dataclasses import replace
import re
from typing import Any

from pydantic import ValidationError

from kg_build_system.kernel.model.public.types import CANONICAL_UNIT_NAMES, UnitTypeName, is_canonical_unit_name
from ....model._private.generated import GeneratedField, GeneratedNullableType, GeneratedType, Nullability
from ....model.public.errors import GenerationError
from .config import ColumnOverride
from .mapping import (
    DeclaredOnlyDigest, RefusedDigest, canonical_sql_type, digest_for,
)
from .naming import Paths
from .state import Inference

#: The scope limit of a promotion: an override declares one whole top-level
#: column of one relation, and a nested declaration would need a declared schema
#: instead of sniffing.
NESTED_PROMOTION = (
    "an override declares one whole top-level column of one relation, and a "
    "nested declaration would need read_json(columns={...}), which replaces "
    "sniffing with a declared schema and moves the source's nullability from "
    "defaulted to declared — a separate decision"
)


def promotion_declaration(column: str, canonical: str) -> str:
    """The request text that declares one top-level column's canonical type."""
    return f'override={{"<relation>.{column}": {{"type": {canonical!r}}}}}'


def container_promotion(type_name: str, *, column: str, canonical: UnitTypeName) -> Exception:
    """A promotion names one canonical unit type, which no container has."""
    return GenerationError(
        f"column {column!r} is read as {type_name!r}, a container whose shape is "
        f"digested from the types below it, so "
        f"{promotion_declaration(column, canonical)} has no single canonical type "
        "of the column to declare; a promotion covers a column the reader reports "
        "as a scalar"
    )


_FIXED_ARRAY_ITEM = re.compile(r"(?s)^(.*)\[\d+\]$")


def _array_item_text(type_name: str) -> str | None:
    normalized = type_name.strip()
    if normalized.endswith("[]"):
        return normalized[:-2].strip() or None
    match = _FIXED_ARRAY_ITEM.match(normalized)
    return (match.group(1).strip() or None) if match else None


def _is_struct_text(type_name: str) -> bool:
    normalized = type_name.strip()
    return normalized.upper().startswith("STRUCT(") and normalized.endswith(")")


def promoted_type_name(type_name: str, *, column: str, canonical: UnitTypeName) -> str:
    """The type one top-level column is resolved from once a promotion declares it.

    A promotion says what the author means a column to hold; it does not make a
    refused physical type digestible, because refusal means no meaning-preserving
    canonical form exists rather than that no declaration has been made yet.
    """
    if _array_item_text(type_name) is not None or _is_struct_text(type_name):
        raise container_promotion(type_name, column=column, canonical=canonical)
    digest = digest_for(type_name)
    if digest is None:
        raise GenerationError(f"column {column!r} has unsupported type {type_name!r}")
    if isinstance(digest, RefusedDigest):
        raise GenerationError(
            f"column {column!r} has DuckDB type {type_name!r}, which is rejected: "
            f"{digest.reason}. A rejection is not a gate a declaration lifts: it "
            "says no meaning-preserving canonical type exists for the values the "
            f"source holds, so {promotion_declaration(column, canonical)} cannot "
            "be honoured. Either export the column in a mappable type, or declare "
            "this table outside a generated package."
        )
    if not is_canonical_unit_name(digest.canonical):
        raise container_promotion(type_name, column=column, canonical=canonical)
    return canonical_sql_type(canonical)


def declared_overrides(override: dict[str, dict[str, Any]]) -> dict[str, ColumnOverride]:
    """The request's column overrides, checked as far as the source-free part reaches.

    A key has to be a full column path — a relation path and a whole column name —
    because one column name can appear in many relations of a source, and an
    override reaches exactly the relation it names. A declared type has to be a
    canonical unit name because it becomes a declaration in the contract.
    """
    declared: dict[str, ColumnOverride] = {}
    for key, value in sorted(override.items()):
        parts = key.split(".")
        if len(parts) < 2 or not all(parts):
            raise GenerationError(
                f"override key {key!r} is not a full column path; an override names "
                "<relation path>.<column>, as in 'temperature.recorded_on'"
            )
        try:
            entry = ColumnOverride.model_validate(value)
        except ValidationError as error:
            raise GenerationError(
                f"override of {key!r} declares nothing a column override carries "
                f"(type and/or nullable, unknown keys refused): {error}"
            ) from error
        if entry.type is not None and not is_canonical_unit_name(entry.type):
            raise GenerationError(
                f"the override of {key!r} declares {entry.type!r}, which does not "
                "name a canonical unit type; a type override declares one of "
                + ", ".join(repr(name) for name in sorted(CANONICAL_UNIT_NAMES))
            )
        declared[key] = entry
    return declared


def overridden_field(field_: GeneratedField, nullable: bool) -> GeneratedField:
    """One finished member with the request's nullability override applied.

    The author's word replaces the source's claim in either direction: ``True``
    declines a non-null claim, dropping the member back to defaulted and out of
    the statistics pre-flight; ``False`` asserts one the build guard will test.
    Neither reads the values — an override is a declaration, and the guard is
    what checks it against the data.
    """
    if nullable:
        if field_.nullability is Nullability.DEFAULTED:
            return field_
        value: GeneratedType = field_.value_type
        if not isinstance(value, GeneratedNullableType):
            value = GeneratedNullableType(value)
        return replace(field_, value_type=value, nullability=Nullability.DEFAULTED)
    if field_.nullability is not Nullability.DEFAULTED:
        return field_
    value = field_.value_type
    if isinstance(value, GeneratedNullableType):
        value = value.value
    return replace(field_, value_type=value, nullability=Nullability.DECLARED)


def require_overrides(inference: Inference) -> None:
    """Settle every override against the relations and columns actually reported.

    An unmatched key is a typo or a request left stale by the data; one that
    reaches inside a column is the scope limit, told as such instead of being
    reported beside columns it could have named.
    """
    for key in sorted(set(inference.overrides) - inference.consumed):
        parts = key.split(".")
        relation = ""
        for cut in range(len(parts) - 1, 0, -1):
            if ".".join(parts[:cut]) in inference.columns:
                relation = ".".join(parts[:cut])
                break
        if relation:
            column = ".".join(parts[len(relation.split(".")):])
            if "." in column or column in inference.nested_members:
                raise GenerationError(
                    f"override names {key!r}, which reaches inside column "
                    f"{column.split('.')[0]!r} of relation {relation!r} rather than "
                    f"naming one whole column; {NESTED_PROMOTION}"
                )
            available = ", ".join(
                repr(name) for name in sorted(inference.columns[relation])
            ) or "no columns"
            raise GenerationError(
                f"override names {key!r}, which is not a column relation "
                f"{relation!r} reports; it exposes {available}. An override has to "
                "name a column the reader reports"
            )
        holders = sorted(
            other for other, names in inference.columns.items() if parts[0] in names
        )
        if holders:
            raise GenerationError(
                f"override names {key!r}, whose first path part {parts[0]!r} is a "
                f"column of {', '.join(repr(name) for name in holders)}, not a "
                f"relation; an override names <relation path>.<column>, and "
                f"reaching inside a column is its own decision: {NESTED_PROMOTION}"
            )
        available = "; ".join(
            f"relation {name!r} exposes "
            + ", ".join(repr(column) for column in sorted(columns))
            for name, columns in sorted(inference.columns.items())
        ) or "no relation was inferred"
        raise GenerationError(
            f"override names {key!r}, whose relation part is not among those "
            f"inferred: {available}. An override names <relation path>.<column>"
        )


__all__ = [
    "NESTED_PROMOTION", "container_promotion", "declared_overrides",
    "overridden_field", "promoted_type_name", "promotion_declaration",
    "require_overrides",
]
