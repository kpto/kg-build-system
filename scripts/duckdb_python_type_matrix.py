"""Report, for every DuckDB type, the type DuckDB reports and the Python object returned.

Two authoritative sources are used rather than a hand-copied list:

* the engine's own type registry, ``duckdb_types()``, restricted to rows that carry a
  ``type_oid`` - those are canonical logical types, while rows without one are alias
  spellings of them;
* ``DESCRIBE``, which is the string the code-generation type mapping matches on, plus
  ``cursor.description`` ``DuckDBPyType`` ``.id`` and the class of the materialised value.

Because the registry drives the table, a DuckDB upgrade that adds a type adds a row
automatically; a row that reports ``NO SAMPLE`` is a type the script could not build a
non-null value for, and ``FETCH FAILED`` is a type whose value cannot reach Python.

Usage::

    uv run python scripts/duckdb_python_type_matrix.py
    uv run python scripts/duckdb_python_type_matrix.py --format tsv
    uv run python scripts/duckdb_python_type_matrix.py --aliases
    uv run python scripts/duckdb_python_type_matrix.py -o duckdb_type_matrix.md

Prefer ``-o`` over shell redirection on Windows: it writes UTF-8 itself instead of
letting the shell re-encode the child process output.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import duckdb

#: One canonical registry tag mapped to the SQL used to probe it. The first expression
#: that evaluates becomes the sample; the last resort is a null cast, whose Python type
#: is ``NoneType`` and therefore says nothing about the conversion.
_PROBES: dict[str, tuple[str, tuple[str, ...]]] = {
    "bool": ("BOOLEAN", ("TRUE",)),
    "int1": ("TINYINT", ("CAST(1 AS TINYINT)",)),
    "int16": ("SMALLINT", ("CAST(1 AS SMALLINT)",)),
    "int": ("INTEGER", ("CAST(1 AS INTEGER)",)),
    "bigint": ("BIGINT", ("CAST(1 AS BIGINT)",)),
    "hugeint": ("HUGEINT", ("CAST(170141183460469231731687303715884105727 AS HUGEINT)",)),
    "uint8": ("UTINYINT", ("CAST(200 AS UTINYINT)",)),
    "uint16": ("USMALLINT", ("CAST(200 AS USMALLINT)",)),
    "uint32": ("UINTEGER", ("CAST(200 AS UINTEGER)",)),
    "ubigint": ("UBIGINT", ("CAST(18446744073709551615 AS UBIGINT)",)),
    "uhugeint": ("UHUGEINT", ("CAST(1 AS UHUGEINT)",)),
    "bignum": ("BIGNUM", ("CAST(123456789012345678901234567890 AS BIGNUM)",)),
    "float": ("FLOAT", ("CAST(0.1 AS FLOAT)",)),
    "double": ("DOUBLE", ("CAST(0.1 AS DOUBLE)",)),
    "dec": ("DECIMAL(10,2)", ("CAST(1.5 AS DECIMAL(10,2))",)),
    "bpchar": ("VARCHAR", ("CAST('abc' AS VARCHAR)",)),
    "binary": ("BLOB", ("CAST('x' AS BLOB)",)),
    "bit": ("BIT", ("CAST('101' AS BIT)",)),
    "guid": ("UUID", ("CAST('4ac7a9e9-607c-4c8a-84f3-843f0191e3fd' AS UUID)",)),
    "date": ("DATE", ("DATE '2026-01-01'",)),
    "time": ("TIME", ("TIME '10:00:00.123456'",)),
    "time_ns": ("TIME_NS", ("CAST('10:00:00.123456789' AS TIME_NS)",)),
    "time with time zone": (
        "TIME WITH TIME ZONE",
        ("CAST('10:00:00+02' AS TIMETZ)",),
    ),
    "datetime": ("TIMESTAMP", ("TIMESTAMP '2026-01-01 10:00:00.123456'",)),
    "timestamp_s": (
        "TIMESTAMP_S",
        ("CAST(TIMESTAMP '2026-01-01 10:00:00' AS TIMESTAMP_S)",),
    ),
    "timestamp_ms": (
        "TIMESTAMP_MS",
        ("CAST(TIMESTAMP '2026-01-01 10:00:00.123' AS TIMESTAMP_MS)",),
    ),
    "timestamp_ns": (
        "TIMESTAMP_NS",
        ("CAST('2026-01-01 10:00:00.123456789' AS TIMESTAMP_NS)",),
    ),
    "timestamp with time zone": (
        "TIMESTAMP WITH TIME ZONE",
        ("CAST('2026-01-01 10:00:00+02' AS TIMESTAMPTZ)",),
    ),
    "interval": ("INTERVAL", ("INTERVAL 1 DAY",)),
    "list": ("INTEGER[]", ("CAST([1, 2] AS INTEGER[])",)),
    "array": ("INTEGER[3]", ("CAST([1, 2, 3] AS INTEGER[3])",)),
    "map": ("MAP(INTEGER, VARCHAR)", ("CAST(map([1], ['a']) AS MAP(INTEGER, VARCHAR))",)),
    "enum": ("ENUM('a', 'b')", ("CAST('a' AS ENUM('a', 'b'))",)),
    "union": (
        "UNION(num INTEGER, txt VARCHAR)",
        ("CAST(union_value(num := 2) AS UNION(num INTEGER, txt VARCHAR))",),
    ),
    "variant": ("VARIANT", ("CAST(42 AS VARIANT)",)),
    "geometry": ("GEOMETRY", ()),
    "row": ("ROW", ("ROW(1, 2)",)),
    "type": ("TYPE", ()),
    "null": ("NULL", ("NULL",)),
}

#: Context that the sample column cannot carry on its own.
_TAG_NOTES: dict[str, str] = {
    "null": "an untyped NULL column is reported as INTEGER; typeof(NULL) returns the string \"NULL\"",
    "timestamp with time zone": "fetching a value needs the pytz module",
}

#: Types a reader can produce that have no canonical registry row of their own:
#: ``STRUCT`` exposes no ``type_oid`` and ``JSON`` is an extension-provided spelling of
#: ``VARCHAR``, so neither appears in the registry rows this script otherwise walks.
_SUPPLEMENT: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    ("struct", "STRUCT", ("CAST({'a': 1} AS STRUCT(a INTEGER))",), "no registry type_oid"),
    ("JSON", "JSON", ('CAST(\'{"a":1}\' AS JSON)',), "extension alias of VARCHAR"),
)


@dataclass(frozen=True, slots=True)
class Row:
    tag: str
    reported: str
    type_id: str
    python_type: str
    sample: str
    note: str
    sample_sql: str


def _registry_tags(connection: duckdb.DuckDBPyConnection) -> list[str]:
    return [
        str(tag)
        for (tag,) in connection.execute(
            "SELECT type_name FROM duckdb_types() WHERE type_oid IS NOT NULL ORDER BY type_oid"
        ).fetchall()
    ]


def _alias_names(connection: duckdb.DuckDBPyConnection) -> list[str]:
    return [
        str(name)
        for (name,) in connection.execute(
            "SELECT DISTINCT type_name FROM duckdb_types() "
            "WHERE type_oid IS NULL ORDER BY type_name"
        ).fetchall()
    ]


def _python_name(value: Any) -> str:
    kind = type(value)
    module = getattr(kind, "__module__", "")
    return kind.__name__ if module == "builtins" else f"{module}.{kind.__name__}"


def _brief(value: Any, limit: int = 30) -> str:
    text = repr(value).replace("\n", " ")
    return text if len(text) <= limit else f"{text[: limit - 1]}…"


def _describe(connection: duckdb.DuckDBPyConnection, expression: str) -> tuple[str, str]:
    """The reported column type and the ``DuckDBPyType`` id for one expression."""
    relation = connection.execute(f"SELECT {expression} AS value")
    reported = str(relation.description[0][1])
    logical = relation.description[0][1]
    try:
        identifier = str(logical.id)
    except Exception:  # noqa: BLE001 - ids are absent for some internal type objects
        identifier = ""
    return reported, identifier


def _probe(connection: duckdb.DuckDBPyConnection, tag: str, fallback: str, candidates: Sequence[str]) -> Row:
    for expression in candidates:
        try:
            reported, identifier = _describe(connection, expression)
        except Exception:  # noqa: BLE001 - a candidate that will not build is tried, then passed over
            continue
        try:
            value = connection.execute(f"SELECT {expression} AS value").fetchone()[0]
        except Exception as error:  # noqa: BLE001 - a type DuckDB reports but cannot hand over
            return Row(
                tag,
                reported,
                identifier,
                "<fetch failed>",
                "",
                str(error).splitlines()[0],
                expression,
            )
        note = ""
        try:
            json.dumps({"v": value})
        except TypeError as error:
            note = f"not JSON-serialisable: {str(error).split(' is not')[0]}"
        return Row(
            tag=tag,
            reported=reported,
            type_id=identifier,
            python_type=_python_name(value),
            sample=_brief(value),
            note=note,
            sample_sql=expression,
        )

    try:
        reported, identifier = _describe(connection, f"CAST(NULL AS {fallback})")
    except Exception as error:  # noqa: BLE001 - some tags have no usable cast syntax
        return Row(tag, "", "", "", "", f"no probe works: {str(error).splitlines()[0]}", "")
    return Row(
        tag,
        reported,
        identifier,
        "NoneType",
        "None",
        "no non-null sample constructible",
        f"CAST(NULL AS {fallback})",
    )


def _matrix(connection: duckdb.DuckDBPyConnection) -> list[Row]:
    rows: list[Row] = []
    for tag in _registry_tags(connection):
        fallback, candidates = _PROBES.get(tag, (tag.upper(), ()))
        row = _probe(connection, tag, fallback, candidates)
        extra = _TAG_NOTES.get(tag, "")
        rows.append(replace(row, note=f"{row.note}; {extra}".strip("; ") if extra else row.note))
    for tag, fallback, candidates, why in _SUPPLEMENT:
        row = _probe(connection, tag, fallback, candidates)
        rows.append(replace(row, note=f"{row.note} ({why})".strip(" ()")))
    return rows


def _alias_matrix(connection: duckdb.DuckDBPyConnection) -> list[Row]:
    rows: list[Row] = []
    for name in _alias_names(connection):
        try:
            reported, identifier = _describe(connection, f"CAST(NULL AS {name})")
        except Exception as error:  # noqa: BLE001 - an unusable spelling is worth reporting
            rows.append(Row(name, "", "", "", "", str(error).splitlines()[0], ""))
            continue
        rows.append(Row(name, reported, identifier, "NoneType", "None", "null cast", ""))
    return rows


def _render(rows: Sequence[Row], style: str) -> str:
    headers = ("Registry tag", "DuckDB type", "DuckDBPyType id", "Python object type", "Sample", "Note")
    table = [
        (row.tag, row.reported, row.type_id, row.python_type, row.sample, row.note) for row in rows
    ]

    if style == "json":
        return json.dumps([asdict(row) for row in rows], indent=2)
    if style in {"tsv", "csv"}:
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter="\t" if style == "tsv" else ",", lineterminator="\n")
        writer.writerow(headers + ("probe",))
        for row, values in zip(rows, table, strict=True):
            writer.writerow((*values, row.sample_sql))
        return buffer.getvalue().rstrip("\n")

    widths = [
        max(len(str(header)), *(len(str(value[index])) for value in table)) if table else len(str(header))
        for index, header in enumerate(headers)
    ]
    lines = [
        "| " + " | ".join(str(header).ljust(width) for header, width in zip(headers, widths, strict=True)) + " |",
        "|" + "|".join("-" * (width + 2) for width in widths) + "|",
    ]
    for values in table:
        lines.append(
            "| " + " | ".join(str(value).ljust(width) for value, width in zip(values, widths, strict=True)) + " |"
        )
    return "\n".join(lines)


def _sibling(path: Path, suffix: str) -> Path:
    return path.with_name(f"{path.stem}-{suffix}{path.suffix}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--format", choices=("markdown", "tsv", "csv", "json"), default="markdown")
    parser.add_argument(
        "--aliases",
        action="store_true",
        help="also report what each registered alias spelling is reported as",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help=(
            "write UTF-8 to this path instead of stdout. Markdown keeps both tables in one file; "
            "tsv, csv and json write the alias table beside it as '<name>-aliases.<ext>'"
        ),
    )
    arguments = parser.parse_args(argv)

    connection = duckdb.connect()
    heading = f"# duckdb {duckdb.__version__} - {len(_registry_tags(connection))} canonical type tags"
    blocks = [_render(_matrix(connection), arguments.format)]
    if arguments.aliases:
        blocks.append(_render(_alias_matrix(connection), arguments.format))

    if arguments.output is None:
        if arguments.format == "markdown":
            print(f"{heading}\n")
            print("\n\n# alias spellings\n\n".join(blocks))
        else:
            print("\n\n".join(blocks))
        return 0

    if arguments.format == "markdown":
        titled = [f"{heading}\n\n{blocks[0]}"] + [f"# alias spellings\n\n{block}" for block in blocks[1:]]
        arguments.output.write_text("\n\n".join(titled) + "\n", encoding="utf-8", newline="\n")
        print(arguments.output)
        return 0

    paths = [arguments.output] + [_sibling(arguments.output, "aliases") for _ in blocks[1:]]
    for block, path in zip(blocks, paths, strict=True):
        path.write_text(block + "\n", encoding="utf-8", newline="\n")
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
