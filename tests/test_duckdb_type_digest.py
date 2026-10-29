"""The digest gate stays complete against the live DuckDB type surface.

``DUCKDB_TYPE_ACCEPTANCE_MATRIX.md`` is the normative record of what each DuckDB
type does, and it says its own validation belongs here: the shipped table is
compared against ``duckdb_types()`` in both directions, so an engine upgrade that
adds, renames or drops a type fails a test rather than leaving the table — and
every definition built on it — quietly stale. The matrix's dispositions are
restated here as expected values, so the data cannot drift from the decision it
records either.
"""

from __future__ import annotations

import unittest

import duckdb

from kg_build_system.engines.interfaces import (
    ARRAY_CANONICAL,
    CANONICAL_SQL_TYPES,
    DIGEST_TABLE,
    EXTENSION_CONDITIONAL_TYPE_NAMES,
    STRUCT_CANONICAL,
    TYPE_NAME_ALIASES,
    CanonicalDigest,
    DeclaredOnlyDigest,
    RefusedDigest,
    canonical_sql_type,
    canonical_type_name,
    digest_for,
)
from kg_build_system.types.interfaces import CANONICAL_UNIT_NAMES

DISPOSITIONS = ("canonical", "declared_only", "refused")

#: The matrix's ``accept`` rows, as the names DuckDB reports for them. The three
#: containers carry their canonical shape by item or member rather than by name.
ACCEPTED = (
    "ARRAY", "BIGINT", "BOOLEAN", "DATE", "DOUBLE", "ENUM", "FLOAT", "INTEGER",
    "LIST", "SMALLINT", "STRUCT", "TIME", "TIMESTAMP", "TIMESTAMP_MS",
    "TIMESTAMP_S", "TINYINT", "UUID", "UTINYINT", "UINTEGER", "USMALLINT",
    "VARCHAR",
)

#: The matrix's ``declared`` rows: the only cast that reaches a canonical type
#: narrows, so an author declaration has to ask for it.
DECLARED = ("HUGEINT", "TIME_NS", "TIMESTAMP_NS", "UBIGINT", "UHUGEINT")

#: The matrix's ``reject`` rows, plus GEOGRAPHY, which the spatial extension
#: provides the same way as GEOMETRY.
REJECTED = (
    "BIGNUM", "BIT", "BLOB", "DECIMAL", "GEOGRAPHY", "GEOMETRY", "INTERVAL",
    "MAP", "NULL", "ROW", "TIME WITH TIME ZONE", "TIMESTAMP WITH TIME ZONE",
    "TYPE", "UNION", "VARIANT",
)

#: ``(expression, reported type, disposition, canonical type)`` measured against
#: the live engine, covering each disposition and the spellings that appear only
#: once a type carries parameters or is reported under one of its aliases.
MEASURED: tuple[tuple[str, str, str, str | None], ...] = (
    ("true", "BOOLEAN", "canonical", "bool"),
    ("1::TINYINT", "TINYINT", "canonical", "int"),
    ("1::SMALLINT", "SMALLINT", "canonical", "int"),
    ("1::INTEGER", "INTEGER", "canonical", "int"),
    ("1::BIGINT", "BIGINT", "canonical", "int"),
    ("1::UTINYINT", "UTINYINT", "canonical", "int"),
    ("1::USMALLINT", "USMALLINT", "canonical", "int"),
    ("1::UINTEGER", "UINTEGER", "canonical", "int"),
    ("1::UBIGINT", "UBIGINT", "declared_only", "int"),
    ("1::HUGEINT", "HUGEINT", "declared_only", "int"),
    ("1::UHUGEINT", "UHUGEINT", "declared_only", "int"),
    ("1.5::FLOAT", "FLOAT", "canonical", "float"),
    ("1.5::DOUBLE", "DOUBLE", "canonical", "float"),
    ("1.5::DECIMAL(18,3)", "DECIMAL(18,3)", "refused", None),
    ("'x'", "VARCHAR", "canonical", "str"),
    ("'{}'::JSON", "JSON", "canonical", "str"),
    ("'a'::ENUM('a', 'b')", "ENUM('a', 'b')", "canonical", "str"),
    ("gen_random_uuid()", "UUID", "canonical", "uuid"),
    ("'2026-08-02'::DATE", "DATE", "canonical", "date"),
    ("'10:00:00'::TIME", "TIME", "canonical", "time"),
    ("'10:00:00'::TIME_NS", "TIME_NS", "declared_only", "time"),
    ("'2026-08-02 10:00:00'::TIMESTAMP", "TIMESTAMP", "canonical", "timestamp"),
    ("'2026-08-02 10:00:00'::TIMESTAMP_S", "TIMESTAMP_S", "canonical", "timestamp"),
    ("'2026-08-02 10:00:00'::TIMESTAMP_MS", "TIMESTAMP_MS", "canonical", "timestamp"),
    ("'2026-08-02 10:00:00'::TIMESTAMP_NS", "TIMESTAMP_NS", "declared_only", "timestamp"),
    ("'2026-08-02 10:00:00+02'::TIMESTAMPTZ", "TIMESTAMP WITH TIME ZONE", "refused", None),
    ("'10:00:00+02'::TIMETZ", "TIME WITH TIME ZONE", "refused", None),
    ("'1 day'::INTERVAL", "INTERVAL", "refused", None),
    ("'0101'::BIT", "BIT", "refused", None),
    ("'x'::BLOB", "BLOB", "refused", None),
    ("1::BIGNUM", "BIGNUM", "refused", None),
    ("MAP([1],[2])", "MAP(INTEGER, INTEGER)", "refused", None),
    ("'1'::VARIANT", "VARIANT", "refused", None),
)


def live_tags() -> tuple[tuple[str, str], ...]:
    """``(tag, reported name)`` for every canonical type tag of the live engine.

    A row carries a ``type_oid`` only when it names a type a column can hold; the
    rest of ``duckdb_types()`` is the spellings an author may write instead.
    """
    rows = duckdb.sql(
        "SELECT type_name, logical_type FROM duckdb_types() "
        "WHERE type_oid IS NOT NULL ORDER BY type_oid"
    ).fetchall()
    return tuple((str(row[0]), str(row[1]).upper()) for row in rows)


def live_names() -> frozenset[str]:
    """Every type name the live engine knows, canonical spelling or alias."""
    rows = duckdb.sql("SELECT DISTINCT type_name, logical_type FROM duckdb_types()").fetchall()
    return frozenset(
        {str(row[0]).upper() for row in rows} | {str(row[1]).upper() for row in rows}
    )


def disposition(value: str) -> tuple[str, str | None]:
    """``(disposition, canonical type)`` the gate reaches for one type name."""
    digest = digest_for(value)
    if digest is None:
        return ("unclassified", None)
    canonical = getattr(digest, "canonical", None)
    return (digest.disposition, canonical)


class DigestTableCompletenessTests(unittest.TestCase):
    def test_every_live_canonical_tag_is_classified_exactly_once(self) -> None:
        tags = live_tags()
        self.assertGreater(len(tags), 30, "expected the engine's whole type surface")
        self.assertEqual(
            len({name for _tag, name in tags}), len(tags),
            "two type tags now report one name, which would let a single entry "
            "classify two types and this test could no longer tell them apart",
        )
        for tag, name in tags:
            with self.subTest(tag=tag, name=name):
                digest = DIGEST_TABLE.get(name)
                self.assertIsNotNone(
                    digest,
                    f"the engine reports {name!r} for type tag {tag!r}, which the "
                    "digest table classifies nowhere",
                )
                assert digest is not None
                self.assertIn(digest.disposition, DISPOSITIONS)
                self.assertIs(
                    digest_for(name), digest, "one reported name, one classification",
                )

    def test_no_live_tag_is_classified_twice(self) -> None:
        reported = {name for _tag, name in live_tags()}
        self.assertFalse(
            set(TYPE_NAME_ALIASES) & reported,
            "an alias that is also a table key would classify one name twice",
        )
        for alias, target in sorted(TYPE_NAME_ALIASES.items()):
            with self.subTest(alias=alias):
                self.assertIn(target, DIGEST_TABLE, f"{alias!r} aliases no key")
                self.assertEqual(
                    digest_for(alias), DIGEST_TABLE[target],
                    "an alias and the name it reports must digest identically",
                )

    def test_no_table_key_is_unreachable(self) -> None:
        live = live_names()
        for name in sorted(DIGEST_TABLE):
            with self.subTest(name=name):
                self.assertIn(
                    name, live | EXTENSION_CONDITIONAL_TYPE_NAMES,
                    f"{name!r} is a key no live type tag, reported name or "
                    "parameterised family can reach; DESCRIBE normalises what it "
                    "reports, so an unreachable key reads as a decision that never "
                    "fires",
                )

    def test_the_table_covers_the_matrix_and_nothing_else(self) -> None:
        by_disposition: dict[str, list[str]] = {kind: [] for kind in DISPOSITIONS}
        for name, digest in DIGEST_TABLE.items():
            by_disposition[digest.disposition].append(name)
        for kind, expected in (
            ("canonical", ACCEPTED), ("declared_only", DECLARED), ("refused", REJECTED),
        ):
            self.assertEqual(
                sorted(by_disposition[kind]), sorted(expected),
                f"the matrix's {kind!r} rows are the decision; the table must carry "
                "them and nothing else",
            )

    def test_the_gate_classifies_representative_types_as_the_matrix_says(self) -> None:
        for _expression, reported, expected, canonical in MEASURED:
            with self.subTest(type=reported):
                self.assertEqual(disposition(reported), (expected, canonical))

    def test_a_name_the_engine_does_not_have_is_not_a_refusal(self) -> None:
        self.assertIsNone(digest_for("SOMETHING_NOVEL"))
        self.assertIsNone(digest_for("VARINT"), "the engine reports VARINT as BIGNUM")
        self.assertIsNone(digest_for("TEXT"), "DESCRIBE reports TEXT as VARCHAR")
        self.assertIsNone(digest_for("REAL"), "DESCRIBE reports REAL as FLOAT")

    def test_parameters_and_aliases_resolve_to_one_entry(self) -> None:
        cases = {
            "DECIMAL(18,2)": "DECIMAL",
            "MAP(VARCHAR, VARCHAR)": "MAP",
            "ENUM('a', 'b')": "ENUM",
            "STRUCT(a INTEGER)": "STRUCT",
            "UNION(num INTEGER, txt VARCHAR)": "UNION",
            "json": "VARCHAR",
            "timestamptz": "TIMESTAMP WITH TIME ZONE",
            "TIMETZ": "TIME WITH TIME ZONE",
        }
        for spelling, key in cases.items():
            with self.subTest(spelling=spelling):
                self.assertEqual(digest_for(spelling), DIGEST_TABLE[key])
        self.assertEqual(canonical_type_name("  decimal(3, 1)"), "DECIMAL")
        self.assertEqual(canonical_type_name("timestamp with time zone"),
                         "TIMESTAMP WITH TIME ZONE")


class DigestTableShapeTests(unittest.TestCase):
    def test_every_entry_carries_the_fact_its_disposition_promises(self) -> None:
        for name, digest in sorted(DIGEST_TABLE.items()):
            with self.subTest(name=name):
                if isinstance(digest, RefusedDigest):
                    self.assertTrue(digest.reason.strip(), f"{name!r} refuses unexplained")
                    continue
                if isinstance(digest, DeclaredOnlyDigest):
                    self.assertTrue(
                        digest.narrowing.strip(), f"{name!r} narrows unexplained",
                    )
                self.assertIsInstance(digest, (CanonicalDigest, DeclaredOnlyDigest))
                self.assertIn(
                    digest.canonical,
                    set(CANONICAL_UNIT_NAMES) | {ARRAY_CANONICAL, STRUCT_CANONICAL},
                    f"{name!r} digests towards an unknown canonical type",
                )

    def test_a_declared_type_narrows_towards_a_unit_with_a_canonical_cast(self) -> None:
        for name in DECLARED:
            with self.subTest(name=name):
                digest = DIGEST_TABLE[name]
                assert isinstance(digest, DeclaredOnlyDigest)
                self.assertEqual(
                    canonical_sql_type(digest.canonical),
                    {"UBIGINT": "BIGINT", "HUGEINT": "BIGINT", "UHUGEINT": "BIGINT",
                     "TIME_NS": "TIME", "TIMESTAMP_NS": "TIMESTAMP"}[name],
                )

    def test_canonical_unit_types_have_their_canonical_sql_type(self) -> None:
        self.assertEqual(
            dict(CANONICAL_SQL_TYPES),
            {
                "bool": "BOOLEAN", "int": "BIGINT", "float": "DOUBLE",
                "str": "VARCHAR", "date": "DATE", "time": "TIME",
                "timestamp": "TIMESTAMP", "uuid": "UUID",
            },
        )
        self.assertEqual(set(CANONICAL_SQL_TYPES), set(CANONICAL_UNIT_NAMES))
        for canonical in CANONICAL_UNIT_NAMES:
            with self.subTest(canonical=canonical):
                self.assertEqual(
                    canonical_sql_type(canonical), CANONICAL_SQL_TYPES[canonical],
                )

    def test_a_container_composes_its_sql_type(self) -> None:
        for container in (ARRAY_CANONICAL, STRUCT_CANONICAL):
            with self.subTest(container=container):
                with self.assertRaises(ValueError):
                    canonical_sql_type(container)
        self.assertEqual(disposition("LIST"), ("canonical", ARRAY_CANONICAL))
        self.assertEqual(disposition("ARRAY"), ("canonical", ARRAY_CANONICAL))
        self.assertEqual(disposition("STRUCT"), ("canonical", STRUCT_CANONICAL))

    def test_an_extension_only_type_is_declared_as_such(self) -> None:
        self.assertEqual(EXTENSION_CONDITIONAL_TYPE_NAMES, frozenset({"GEOGRAPHY"}))
        self.assertEqual(disposition("GEOGRAPHY"), ("refused", None))


class LiveReportedSpellingTests(unittest.TestCase):
    """The keys are the names the engine actually prints, not names of our own."""

    def test_what_describe_reports_digests_as_the_matrix_says(self) -> None:
        select = ", ".join(
            f"{expression} AS c{index}"
            for index, (expression, *_rest) in enumerate(MEASURED)
        )
        reported = [
            str(row[1]) for row in duckdb.sql(f"DESCRIBE SELECT {select}").fetchall()
        ]
        self.assertEqual(
            reported, [entry[1] for entry in MEASURED],
            "the engine no longer reports the spellings this table is keyed on",
        )
        for entry, printed in zip(MEASURED, reported, strict=True):
            with self.subTest(type=printed):
                self.assertEqual(
                    disposition(printed), (entry[2], entry[3]),
                    f"a column DuckDB reports as {printed!r} must digest as measured",
                )

    def test_arrays_are_reported_around_their_item_type(self) -> None:
        reported = [
            str(row[1]) for row in duckdb.sql(
                "DESCRIBE SELECT [1,2,3]::INTEGER[] AS list_, [1,2,3]::INTEGER[3] AS fixed_"
            ).fetchall()
        ]
        self.assertEqual(reported, ["INTEGER[]", "INTEGER[3]"])
        self.assertEqual(disposition("INTEGER"), ("canonical", "int"))


if __name__ == "__main__":
    unittest.main()
