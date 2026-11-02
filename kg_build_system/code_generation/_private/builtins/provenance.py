"""Source provenance: schema facts, digest, nullability notes and pre-flight."""
from __future__ import annotations

import hashlib
import logging

import duckdb

from ...internal.ir import NullabilityNote
from .formats import (
    PARQUET_SUFFIXES, SchemaTier, source_label, source_suffix,
)
from .observation import DescribedColumn, declared_null_statistics
from .state import Inference

_LOGGER = logging.getLogger("kg_build_system.code_generation.inference")


def schema_facts(
    *,
    class_name: str,
    relation: str,
    sources: tuple[str, ...],
    hive_partitioned: bool,
    described: tuple[DescribedColumn, ...],
    node_shape: tuple[tuple[str, str, str | None], ...],
) -> list[str]:
    """The observed schema of one relation, in a digestible normalized form.

    Only schema-bearing facts are recorded — never file bytes, names, sizes,
    or locations — so row churn and machine layout leave the digest alone
    while any change to columns, types, nullability, or nested shape moves it.
    """
    facts = [
        f"relation {relation} class {class_name} sources {len(sources)} hive {int(hive_partitioned)}",
    ]
    facts.extend(
        f"column {column.name} {column.type_name} {column.nullability.value}"
        for column in described
    )
    facts.extend(f"node {name} {repetition} {duckdb_type}" for name, repetition, duckdb_type in node_shape)
    return facts


def schema_digest(inference: Inference) -> str:
    return hashlib.sha256("\n".join(inference.schema_facts).encode(encoding="utf-8")).hexdigest()


def nullability_note(
    tier: SchemaTier,
    source: str,
    sources: tuple[str, ...],
    relation: str,
    declarations: tuple[str, ...] = (),
) -> NullabilityNote:
    label = source_label(source, sources)
    if tier == "enforced":
        line = f"nullability: enforced by relation '{relation}' in {label} (NOT NULL)"
    elif tier == "declared":
        line = f"nullability: declared by {label} (required/optional)"
    else:
        line = f"nullability: not declared by {label} - all members nullable"
    return NullabilityNote(line, tuple(sources), declarations)


def report_null_statistics(
    connection: duckdb.DuckDBPyConnection, sources: tuple[str, ...], declared: set[str],
) -> None:
    """Test declared non-nullability against the file's own column statistics.

    The declared set is scoped to one relation: the same path is a separate
    claim in every relation that carries it, and one relation's claim must not
    be tested — or reported — through another's files. A statistic tests a
    claim, it never sets or enforces one, so this reports and never fails.
    """
    if source_suffix(sources[0]) not in PARQUET_SUFFIXES or not declared:
        return
    report = declared_null_statistics(connection, sources, sorted(declared))
    for statistic in report.violations:
        _LOGGER.warning(
            "%s reports %d null value(s) in %d rows for the declared non-null "
            "column %r; inference will keep claiming it is non-null until the "
            "request says otherwise, and the build guard will abort on it",
            source_label(sources[0], sources), statistic.nulls, statistic.values,
            statistic.schema_path,
        )
    for path in report.unknown_paths:
        _LOGGER.debug("no null statistics published for %r; unknown is not zero", path)


__all__ = ["nullability_note", "report_null_statistics", "schema_digest", "schema_facts"]
