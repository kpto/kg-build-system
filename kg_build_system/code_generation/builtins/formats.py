"""Source formats, suffix classification and labels for inference."""
from __future__ import annotations

from pathlib import Path
import re
from typing import Final, Literal
from urllib.parse import urlparse

DATABASE_SUFFIXES: Final = frozenset({".db", ".ddb", ".duckdb"})
REMOTE_SCHEMES: Final = frozenset({"http", "https", "s3"})
DATA_SUFFIXES: Final = frozenset({
    ".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".parquet", ".pq",
})
PARQUET_SUFFIXES: Final = frozenset({".parquet", ".pq"})
PARQUET_LIST_WRAPPERS: Final = frozenset({"list", "element"})
HIVE_PARTITION: Final = re.compile(r"^[^/=]+=[^/]+$")

#: The three levels of schema trust of the source-schema specification.
SchemaTier = Literal["enforced", "declared", "defaulted"]


def remote_source(value: str) -> bool:
    """Whether ``value`` is a DuckDB-readable remote object URL."""
    return urlparse(value).scheme.lower() in REMOTE_SCHEMES


def source_suffix(value: str) -> str:
    """Return a source suffix without treating a URL query as part of its name."""
    return Path(urlparse(value).path if remote_source(value) else value).suffix.lower()


def source_stem(value: str) -> str:
    return Path(urlparse(value).path if remote_source(value) else value).stem


def source_label(source: str, sources: tuple[str, ...]) -> str:
    """How one physical source is named in a generated provenance header."""
    name = Path(urlparse(source).path if remote_source(source) else source).name
    label = f"{name} ({source_suffix(source).lstrip('.')})"
    if len(sources) > 1:
        return f"{label} and {len(sources) - 1} more file(s)"
    return label


def tier_for_suffix(suffix: str) -> SchemaTier:
    """One tier decision per source: database, Parquet, or defaulted."""
    if suffix in DATABASE_SUFFIXES:
        return "enforced"
    if suffix in PARQUET_SUFFIXES:
        return "declared"
    return "defaulted"


__all__ = [
    "DATA_SUFFIXES", "DATABASE_SUFFIXES", "HIVE_PARTITION",
    "PARQUET_LIST_WRAPPERS", "PARQUET_SUFFIXES", "REMOTE_SCHEMES", "SchemaTier",
    "remote_source", "source_label", "source_stem", "source_suffix",
    "tier_for_suffix",
]
