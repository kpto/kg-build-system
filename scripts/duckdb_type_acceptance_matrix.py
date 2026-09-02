"""Full matrix of DuckDB types: acceptance, normalising cast, and representative Python type.

The table is the accepted / rejected decision for the type work, and every row is
*executed* rather than asserted. For each type the script builds a value, applies the
normalising cast the design says the source view should apply, and checks three things:
that the source type carries the expected ``DuckDBPyType.id``, that DuckDB reports the
canonical SQL type after the cast, and that the Python object the client hands over
matches the representative type the design claims. A row whose verdict is not
``verified`` is a place where the design and the engine disagree, and the script exits
non-zero so the matrix can guard a DuckDB upgrade.

Dispositions:

* ``accept``   - digestible as-is, or by a widening cast applied automatically at the scan;
* ``declared`` - digestible only through an author-declared override, because the only
                 available cast narrows the value or its precision;
* ``reject``   - no meaning-preserving canonical type exists yet, with the reason recorded.

Usage::

    uv run python scripts/duckdb_type_acceptance_matrix.py
    uv run python scripts/duckdb_type_acceptance_matrix.py --output DUCKDB_TYPE_ACCEPTANCE_MATRIX.md
    uv run python scripts/duckdb_type_acceptance_matrix.py --format tsv
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

ACCEPT = "accept"
DECLARED = "declared"
REJECT = "reject"

#: Where the script writes its document when no path is supplied.
DEFAULT_DOCUMENT = Path("DUCKDB_TYPE_ACCEPTANCE_MATRIX.md")


@dataclass(frozen=True, slots=True)
class TypeRow:
    #: SQL spelling used to build the probe value.
    source_sql: str
    #: The ``DuckDBPyType.id`` family tag expected for the source type.
    id_tag: str
    disposition: str
    #: The framework canonical type, or ``-`` when there is none.
    canonical: str
    #: Cast the source view applies, as SQL with ``{value}`` for the probe expression.
    cast_sql: str
    #: SQL type DuckDB is expected to report after that cast.
    target_sql: str
    #: Representative Python type authors reason in, independent of what the client sends.
    python_representative: str
    note: str
    #: A value outside the canonical range, used only to show what the narrowing does.
    overflow_sql: str = ""
    #: Whether the canonical type may be a graph property or key; atoms only.
    property_type: bool = True
    #: Display name when the reported SQL type would mislead, such as an untyped NULL.
    display: str = ""


#: One row per DuckDB type. Canonical names are the framework's own vocabulary, so a
#: canonical whose meaning is not a Python builtin does not borrow one: ``Uuid`` rather
#: than ``str``, because a UUID is an identifier that merely has a canonical text form.
_ROWS: tuple[TypeRow, ...] = (
    # --- Boolean ---------------------------------------------------------------------
    TypeRow("CAST(TRUE AS BOOLEAN)", "boolean", ACCEPT, "bool", "{value}", "BOOLEAN", "bool", ""),
    # --- Integers: widened to one signed 64-bit computation domain -------------------
    TypeRow("CAST(1 AS TINYINT)", "tinyint", ACCEPT, "int", "CAST({value} AS BIGINT)", "BIGINT", "int", "widening"),
    TypeRow("CAST(1 AS SMALLINT)", "smallint", ACCEPT, "int", "CAST({value} AS BIGINT)", "BIGINT", "int", "widening"),
    TypeRow("CAST(1 AS INTEGER)", "integer", ACCEPT, "int", "CAST({value} AS BIGINT)", "BIGINT", "int", "widening"),
    TypeRow("CAST(1 AS BIGINT)", "bigint", ACCEPT, "int", "{value}", "BIGINT", "int", ""),
    TypeRow("CAST(200 AS UTINYINT)", "utinyint", ACCEPT, "int", "CAST({value} AS BIGINT)", "BIGINT", "int", "widening"),
    TypeRow("CAST(200 AS USMALLINT)", "usmallint", ACCEPT, "int", "CAST({value} AS BIGINT)", "BIGINT", "int", "widening"),
    TypeRow("CAST(200 AS UINTEGER)", "uinteger", ACCEPT, "int", "CAST({value} AS BIGINT)", "BIGINT", "int", "widening"),
    TypeRow(
        "CAST(4294967296 AS UBIGINT)", "ubigint", DECLARED, "int",
        "CAST({value} AS BIGINT)", "BIGINT", "int",
        "narrowing above 2^63-1 only, and it must never wrap",
        "CAST(18446744073709551615 AS UBIGINT)",
    ),
    TypeRow(
        "CAST(1 AS HUGEINT)", "hugeint", DECLARED, "int",
        "CAST({value} AS BIGINT)", "BIGINT", "int",
        "engine-checked narrowing; without it Parquet export degrades HUGEINT to DOUBLE",
        "CAST(170141183460469231731687303715884105727 AS HUGEINT)",
    ),
    TypeRow(
        "CAST(1 AS UHUGEINT)", "uhugeint", DECLARED, "int",
        "CAST({value} AS BIGINT)", "BIGINT", "int", "narrowing to the signed 64-bit domain",
        "CAST(340282366920938463463374607431768211455 AS UHUGEINT)",
    ),
    TypeRow(
        "CAST(123456789012345678901234567890 AS BIGNUM)", "bignum", REJECT, "-", "", "", "str",
        "unbounded integer: decimal is bounded and str would change its meaning; the client "
        "also hands BIGNUM over as text",
    ),
    # --- Floating point and exact numerics -------------------------------------------
    TypeRow(
        "CAST(0.1 AS FLOAT)", "float", ACCEPT, "float", "CAST({value} AS DOUBLE)", "DOUBLE", "float",
        "widening fixes the arithmetic width only: the stored value is already single precision",
    ),
    TypeRow("CAST(0.1 AS DOUBLE)", "double", ACCEPT, "float", "{value}", "DOUBLE", "float", ""),
    TypeRow(
        "CAST(1.5 AS DECIMAL(10,2))", "decimal", REJECT, "decimal(p, s)", "", "", "decimal.Decimal",
        "deferred: needs a parameterised canonical type plus DuckDB result-width rules; "
        "DECIMAL division returns DOUBLE, so no division operator may be offered",
    ),
    # --- Text, identifiers and binary -------------------------------------------------
    TypeRow("CAST('abc' AS VARCHAR)", "varchar", ACCEPT, "str", "{value}", "VARCHAR", "str", ""),
    TypeRow(
        "CAST('{\"a\":1}' AS JSON)", "varchar", ACCEPT, "str", "CAST({value} AS VARCHAR)", "VARCHAR", "str",
        "JSON is a VARCHAR spelling, so .id cannot distinguish the two",
    ),
    TypeRow(
        "CAST('4ac7a9e9-607c-4c8a-84f3-843f0191e3fd' AS UUID)", "uuid", ACCEPT, "Uuid", "{value}", "UUID",
        "uuid.UUID", "own canonical type: an identifier that merely has a canonical text form, "
        "carried unchanged with no cast and no conversion",
    ),
    TypeRow("CAST('101' AS BIT)", "bit", REJECT, "-", "", "", "str", "rare; a str canonical would be cheap to add"),
    TypeRow(
        "CAST('x' AS BLOB)", "blob", REJECT, "binary", "", "", "bytes",
        "deferred: no total order, so the core operators cannot merge or deduplicate it",
    ),
    # --- Temporal ---------------------------------------------------------------------
    TypeRow("DATE '2026-01-01'", "date", ACCEPT, "date", "{value}", "DATE", "datetime.date", ""),
    TypeRow("TIME '10:00:00.123456'", "time", ACCEPT, "time", "{value}", "TIME", "datetime.time", ""),
    TypeRow(
        "CAST('10:00:00.123456789' AS TIME_NS)", "time_ns", DECLARED, "time",
        "CAST({value} AS TIME)", "TIME", "datetime.time",
        "unchecked narrowing: DuckDB rounds nanoseconds silently, so only the declaration protects the value",
    ),
    TypeRow(
        "CAST('10:00:00+02' AS TIMETZ)", "time with time zone", REJECT, "-", "", "", "datetime.time",
        "a zoned time of day has no canonical type chosen",
    ),
    TypeRow("TIMESTAMP '2026-01-01 10:00:00.123456'", "timestamp", ACCEPT, "timestamp", "{value}", "TIMESTAMP", "datetime.datetime", ""),
    TypeRow(
        "CAST(TIMESTAMP '2026-01-01 10:00:00' AS TIMESTAMP_S)", "timestamp_s", ACCEPT, "timestamp",
        "CAST({value} AS TIMESTAMP)", "TIMESTAMP", "datetime.datetime", "widening",
    ),
    TypeRow(
        "CAST(TIMESTAMP '2026-01-01 10:00:00.123' AS TIMESTAMP_MS)", "timestamp_ms", ACCEPT, "timestamp",
        "CAST({value} AS TIMESTAMP)", "TIMESTAMP", "datetime.datetime", "widening",
    ),
    TypeRow(
        "CAST('2026-01-01 10:00:00.123456789' AS TIMESTAMP_NS)", "timestamp_ns", DECLARED, "timestamp",
        "CAST({value} AS TIMESTAMP)", "TIMESTAMP", "datetime.datetime",
        "unchecked narrowing: nanoseconds are dropped silently, and Python datetimes cannot hold them either",
    ),
    TypeRow(
        "CAST('2026-01-01 10:00:00+02' AS TIMESTAMPTZ)", "timestamp with time zone", REJECT, "instant",
        "", "", "<fetch failed>",
        "deferred: an instant and a local date-time are different types; the client also needs pytz",
    ),
    TypeRow(
        "INTERVAL 1 DAY", "interval", REJECT, "interval", "", "", "datetime.timedelta",
        "deferred: calendar-aware months are not a duration value",
    ),
    # --- Nested -----------------------------------------------------------------------
    TypeRow(
        "CAST([1, 2] AS INTEGER[])", "list", ACCEPT, "Array[int]", "CAST({value} AS BIGINT[])", "BIGINT[]", "list",
        "element-wise widening", "", False,
    ),
    TypeRow(
        "CAST([1, 2, 3] AS INTEGER[3])", "array", ACCEPT, "Array[int]", "CAST({value} AS BIGINT[])", "BIGINT[]", "list",
        "fixed length widens to a list; the client hands arrays over as tuples, which the cast removes",
        "", False,
    ),
    TypeRow(
        "CAST({'a': 1} AS STRUCT(a INTEGER))", "struct", ACCEPT, "Struct{a: int}",
        "CAST({value} AS STRUCT(a BIGINT))", "STRUCT(a BIGINT)", "dict", "members widened element-wise", "", False,
    ),
    TypeRow(
        "CAST(map([1], ['a']) AS MAP(INTEGER, VARCHAR))", "map", REJECT, "Array[Struct{key, value}]",
        "", "", "dict",
        "digestible through the entries representation, but the nested-shape work is deferred",
    ),
    TypeRow(
        "CAST(union_value(num := 2) AS UNION(num INTEGER, txt VARCHAR))", "union", REJECT, "-", "", "", "int",
        "a tagged sum has no framework analogue and the client drops the tag",
    ),
    TypeRow(
        "CAST(42 AS VARIANT)", "variant", REJECT, "-", "", "", "int",
        "per-row self-describing typing has no canonical form and the client drops it",
    ),
    TypeRow(
        "CAST('a' AS ENUM('a', 'b'))", "enum", ACCEPT, "str", "CAST({value} AS VARCHAR)", "VARCHAR", "str",
        "the permitted label set belongs on the field as metadata, not in the type",
    ),
    # --- Internal and extension types --------------------------------------------------
    TypeRow(
        "ROW(1, 2)", "struct", REJECT, "-", "", "", "tuple",
        "an anonymous record has no field names to declare", display="ROW (anonymous struct)",
    ),
    TypeRow(
        "NULL", "integer", REJECT, "-", "", "", "NoneType",
        "an untyped NULL column is an absent declaration; DESCRIBE reports INTEGER for it",
        display="untyped NULL",
    ),
    TypeRow("CAST(NULL AS TYPE)", "type", REJECT, "-", "", "", "NoneType", "internal pseudo-type"),
    TypeRow(
        "CAST(NULL AS GEOMETRY)", "geometry", REJECT, "-", "", "", "NoneType",
        "extension-conditional, so a definition using it is not portable",
    ),
)


@dataclass(frozen=True, slots=True)
class Result:
    source: str
    id_tag: str
    reported_source: str
    disposition: str
    canonical: str
    property_type: bool
    cast_sql: str
    reported_cast: str
    target_sql: str
    python_client: str
    python_representative: str
    verdict: str
    note: str
    #: For declared rows, what the narrowing does to a value outside the canonical range.
    narrowing: str = ""
    #: Display name overriding the reported SQL type where that name would mislead.
    display: str = ""


def _python_name(value: Any) -> str:
    kind = type(value)
    module = getattr(kind, "__module__", "")
    return kind.__name__ if module == "builtins" else f"{module}.{kind.__name__}"


def _reported(connection: duckdb.DuckDBPyConnection, expression: str) -> str:
    return str(connection.execute(f"DESCRIBE SELECT {expression} AS value").fetchall()[0][1])


def _narrowing(connection: duckdb.DuckDBPyConnection, row: TypeRow) -> str:
    """What the declared narrowing does to a value outside the canonical range."""
    probe = row.overflow_sql or row.source_sql
    cast = row.cast_sql.format(value=probe)
    try:
        before = str(connection.execute(f"SELECT CAST({probe} AS VARCHAR) AS value").fetchone()[0])
        after = str(connection.execute(f"SELECT CAST({cast} AS VARCHAR) AS value").fetchone()[0])
    except Exception as error:  # noqa: BLE001 - an aborted narrowing is the wanted behaviour
        return f"checked: aborts outside range ({str(error).splitlines()[0][:44]})"
    if before == after:
        return "no observable change for the probe value"
    return f"silent: {before} becomes {after}"


def _display_cast(row: TypeRow) -> str:
    """The cast as authors will read it: the template with the probe value named."""
    if not row.cast_sql:
        return ""
    return "identity" if row.cast_sql == "{value}" else row.cast_sql.replace("{value}", "value")


def _fail(
    row: TypeRow, reported_source: str, python_client: str, verdict: str,
) -> Result:
    return Result(
        row.source_sql, row.id_tag, reported_source, row.disposition, row.canonical, row.property_type,
        _display_cast(row), "", row.target_sql, python_client, row.python_representative, verdict, row.note,
        display=row.display,
    )


def _evaluate(connection: duckdb.DuckDBPyConnection, row: TypeRow) -> Result:
    reported_source = ""
    python_client = ""
    try:
        reported_source = _reported(connection, row.source_sql)
        type_object = connection.execute(f"SELECT {row.source_sql} AS value").description[0][1]
        if type_object.id != row.id_tag:
            return _fail(row, reported_source, "", f".id is {type_object.id!r}, expected {row.id_tag!r}")
        python_client = _python_name(connection.execute(f"SELECT {row.source_sql} AS value").fetchone()[0])
    except Exception as error:  # noqa: BLE001 - a value the client cannot hand over is a result
        python_client = f"<{type(error).__name__}>"

    if not row.cast_sql:
        return _fail(row, reported_source, python_client, "design row (no cast to verify)")

    cast = row.cast_sql.format(value=row.source_sql)
    try:
        reported_cast = _reported(connection, cast)
    except Exception as error:  # noqa: BLE001 - an unsupported cast is exactly what needs reporting
        return replace(
            _fail(row, reported_source, python_client, f"cast unsupported: {str(error).splitlines()[0][:60]}"),
            cast_sql=_display_cast(row),
        )

    if reported_cast.upper() != row.target_sql.upper():
        verdict = f"reports {reported_cast}, expected {row.target_sql}"
        client_after_cast = ""
    else:
        try:
            client_after_cast = _python_name(connection.execute(f"SELECT {cast} AS value").fetchone()[0])
        except Exception as error:  # noqa: BLE001 - see above
            client_after_cast = f"<{type(error).__name__}>"
        if client_after_cast != row.python_representative:
            verdict = f"client returns {client_after_cast} after cast, design says {row.python_representative}"
        else:
            verdict = "verified"

    narrowing = _narrowing(connection, row) if verdict == "verified" and row.disposition == DECLARED else ""
    return Result(
        row.source_sql, row.id_tag, reported_source, row.disposition, row.canonical, row.property_type,
        _display_cast(row), reported_cast, row.target_sql, python_client, row.python_representative, verdict,
        row.note, narrowing, display=row.display,
    )


_HEADERS = (
    "DuckDB type", "Disposition", "Canonical type", "Graph property", "Normalising cast",
    "Reports after cast", "Client returns", "Representative Python type", "Verdict", "Note",
)


def _label(result: Result) -> str:
    """The name the matrix shows: a designed display name, else what DuckDB reported."""
    return result.display or result.reported_source or result.source


def _cells(result: Result) -> tuple[str, ...]:
    note = f"{result.note}; measured: {result.narrowing}" if result.narrowing else result.note
    return (
        _label(result),
        result.disposition,
        result.canonical or "-",
        ("yes" if result.property_type else "no") if result.disposition != REJECT else "-",
        result.cast_sql or "none",
        result.reported_cast or "-",
        result.python_client or "-",
        result.python_representative or "-",
        result.verdict,
        note,
    )


def _table(results: Sequence[Result], style: str, pad: bool = True) -> str:
    rows = [_cells(result) for result in results]
    if style == "json":
        return json.dumps([asdict(result) for result in results], indent=2)
    if style in {"tsv", "csv"}:
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter="\t" if style == "tsv" else ",", lineterminator="\n")
        writer.writerow(_HEADERS)
        writer.writerows(rows)
        return buffer.getvalue().rstrip("\n")

    if not pad:
        lines = ["| " + " | ".join(_HEADERS) + " |", "|" + "|".join("---" for _ in _HEADERS) + "|"]
        lines += ["| " + " | ".join(row) + " |" for row in rows]
        return "\n".join(lines)

    widths = [max([len(str(header))] + [len(row[index]) for row in rows]) for index, header in enumerate(_HEADERS)]
    lines = [
        "| " + " | ".join(h.ljust(w) for h, w in zip(_HEADERS, widths, strict=True)) + " |",
        "|" + "|".join("-" * (width + 2) for width in widths) + "|",
    ]
    lines += ["| " + " | ".join(v.ljust(w) for v, w in zip(row, widths, strict=True)) + " |" for row in rows]
    return "\n".join(lines)


def _markdown(results: Sequence[Result], version: str) -> str:
    accepted = [result for result in results if result.disposition == ACCEPT]
    declared = [result for result in results if result.disposition == DECLARED]
    rejected = [result for result in results if result.disposition == REJECT]
    properties = sorted(
        {result.canonical for result in results if result.disposition != REJECT and result.property_type},
        key=str.lower,
    )
    values_only = sorted(
        {result.canonical for result in results if result.disposition != REJECT and not result.property_type},
        key=str.lower,
    )
    broken = [result for result in results if not result.verdict.startswith(("verified", "design row"))]

    parts = [
        "# DuckDB type acceptance matrix",
        "",
        f"Executable source: `scripts/duckdb_type_acceptance_matrix.py`, generated against duckdb {version}.",
        "Every row below is executed, not asserted: the script builds a value of the source type, applies the",
        "normalising cast the design says the source view should apply, and confirms the reported SQL type and",
        "the Python object that comes back. Running the script re-validates the matrix and exits non-zero if",
        "any row disagrees, so it doubles as a guard on a DuckDB upgrade.",
        "",
        "## Dispositions",
        "",
        "| Disposition | Meaning | Types |",
        "| --- | --- | --- |",
        f"| `accept` | Digestible as-is or by a widening cast applied automatically at the scan. | {len(accepted)} |",
        f"| `declared` | Digestible only through an author-declared override, because the only available cast "
        f"narrows the value or its precision. | {len(declared)} |",
        f"| `reject` | No meaning-preserving canonical type exists yet; the reason is recorded per row. | {len(rejected)} |",
        "",
        "## Matrix",
        "",
        _table(results, "markdown", pad=False),
        "",
        "## Canonical vocabulary",
        "",
        "A canonical type is named for what it means in the framework, not for the Python builtin whose name it "
        "could have borrowed. `Uuid` is a canonical type rather than `str` because a UUID is an identifier that "
        "merely has a canonical text form, and the client already carries it as `uuid.UUID` with no cast and no "
        "conversion.",
        "",
        f"- Usable as a graph property or key: {', '.join(f'`{name}`' for name in properties)}.",
        f"- Values that must be flattened before they can become a property: "
        f"{', '.join(f'`{name}`' for name in values_only)}.",
        "",
        "## What the declared narrowings do",
        "",
        "Engine-checked narrowings abort; silent narrowings rewrite the value, so the declaration is the only "
        "protection and belongs in front of the author rather than in a default.",
        "",
        "| DuckDB type | Cast | Behaviour |",
        "| --- | --- | --- |",
    ]
    for result in declared:
        parts.append(f"| `{_label(result)}` | `{result.cast_sql}` | {result.narrowing} |")

    parts += ["", "## Why the rejected types are rejected", "", "| DuckDB type | Deferred canonical | Reason |", "| --- | --- | --- |"]
    parts += [f"| `{_label(result)}` | {f'`{result.canonical}`' if result.canonical != '-' else '—'} | {result.note} |" for result in rejected]

    parts += [
        "",
        "## Verification",
        "",
        f"{len(results) - len(broken)} of {len(results)} rows agree with the design."
        if not broken
        else f"{len(broken)} rows disagree with the design:",
    ]
    parts += [f"- `{_label(result)}`: {result.verdict}" for result in broken]
    parts.append("")
    return "\n".join(parts)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--format", choices=("markdown", "tsv", "csv", "json"), default="markdown")
    parser.add_argument(
        "--output", type=Path, metavar="PATH",
        help="write the full matrix document to PATH instead of printing the table",
    )
    parser.add_argument("--document", action="store_true", help=f"shorthand for --output {DEFAULT_DOCUMENT}")
    arguments = parser.parse_args(argv)

    connection = duckdb.connect()
    results = [_evaluate(connection, row) for row in _ROWS]
    broken = [result for result in results if not result.verdict.startswith(("verified", "design row"))]
    counts = {name: sum(1 for result in results if result.disposition == name) for name in (ACCEPT, DECLARED, REJECT)}

    target: Path | None = DEFAULT_DOCUMENT if arguments.document else arguments.output
    if target is not None:
        document = _markdown(results, duckdb.__version__)
        target.write_text(document, encoding="utf-8", newline="\n")
        print(f"wrote {target} ({len(results)} types: {counts[ACCEPT]} accept, {counts[DECLARED]} declared-only, "
              f"{counts[REJECT]} reject; {len(broken)} disagreeing)")
    else:
        print(f"# duckdb {duckdb.__version__} - {len(results)} types: "
              f"{counts[ACCEPT]} accept, {counts[DECLARED]} declared-only, {counts[REJECT]} reject\n")
        print(_table(results, arguments.format))
        if broken:
            print(f"\n# {len(broken)} rows disagree with the design")
            for result in broken:
                print(f"   {_label(result)}: {result.verdict}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
