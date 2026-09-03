"""DuckDB SQL for literals whose frozen value is the canonical text of their unit."""
from __future__ import annotations

import json
import unittest
import uuid
from datetime import date, datetime, time

import duckdb

from kg_build_system.engines.duckdb import lower_relation_sql
from kg_build_system.expressions import select_expression, wrap_expression
from kg_build_system.expressions.base import field_reference
from kg_build_system.expressions.ir_codec import decode_expression_ir, encode_expression_ir
from kg_build_system.expressions.literals import literal
from kg_build_system.expressions.mapping import expression_to_ir
from kg_build_system.expressions.models import ExpressionNode, LiteralExpression
from kg_build_system.relational import lower_product
from kg_build_system.types import Array, NullableType, TIME, normalize_type

# Text is what a literal of these units stores, so only the unit on the node can name the
# SQL type — without it the value reaches the scan as a VARCHAR.
TYPED_LITERALS: tuple[tuple[ExpressionNode, str], ...] = (
    (literal(date(2026, 8, 2)), "CAST('2026-08-02' AS DATE)"),
    (literal(time(14, 20)), "CAST('14:20:00' AS TIME)"),
    (literal(datetime(2026, 8, 2, 14, 20)), "CAST('2026-08-02T14:20:00' AS TIMESTAMP)"),
    (literal(datetime(2026, 8, 2, 14, 20, 0, 123456)), "CAST('2026-08-02T14:20:00.123456' AS TIMESTAMP)"),
    (
        literal(uuid.UUID("2f8a1c6e-9b4d-4a53-8f1a-6c0d2e4b8a91")),
        "CAST('2f8a1c6e-9b4d-4a53-8f1a-6c0d2e4b8a91' AS UUID)",
    ),
)

_CONSTANT_SELECT = "SELECT {literal} AS \"value\" FROM (SELECT 1) AS constant_input"

# An array of these units stores an array of canonical text, which on its own is a
# VARCHAR[]; only the item unit on the node names the SQL type its items need.
TYPED_ARRAY_LITERALS: tuple[tuple[ExpressionNode, str], ...] = (
    (literal([date(2026, 1, 1)]), "CAST(['2026-01-01'] AS DATE[])"),
    (literal([time(14, 20)]), "CAST(['14:20:00'] AS TIME[])"),
    (
        literal([datetime(2026, 8, 2, 14, 20)]),
        "CAST(['2026-08-02T14:20:00'] AS TIMESTAMP[])",
    ),
    (
        literal([uuid.UUID("2f8a1c6e-9b4d-4a53-8f1a-6c0d2e4b8a91")]),
        "CAST(['2f8a1c6e-9b4d-4a53-8f1a-6c0d2e4b8a91'] AS UUID[])",
    ),
    # The item unit is what carries the type, so it names the SQL through an optional
    # array, through optional items, and once per level of a nested array.
    (
        literal([date(2026, 1, 1)], logical_type=NullableType(normalize_type(Array[date]))),
        "CAST(['2026-01-01'] AS DATE[])",
    ),
    (
        literal([date(2026, 1, 1), None], logical_type=normalize_type(Array[date | None])),
        "CAST(['2026-01-01', NULL] AS DATE[])",
    ),
    (
        literal([[date(2026, 1, 1)]], logical_type=normalize_type(Array[Array[date]])),
        "CAST([['2026-01-01']] AS DATE[][])",
    ),
    (literal([], logical_type=normalize_type(Array[date])), "CAST([] AS DATE[])"),
)

# An array of a unit that stores JSON rather than text needs no cast to reach its item
# type, so it lowers exactly as it did before the text-canonical units existed.
UNTYPED_ARRAY_LITERALS: tuple[tuple[ExpressionNode, str], ...] = (
    (literal([1, 2]), "[1, 2]"),
    (literal([1.5]), "[1.5]"),
    (literal([True]), "[TRUE]"),
    (literal(["2026-08-02"]), "['2026-08-02']"),
    (literal([[1, 2]]), "[[1, 2]]"),
    (literal([None, 1], logical_type=normalize_type(Array[int | None])), "[NULL, 1]"),
)


def _constant_sql(expression: ExpressionNode) -> str:
    return lower_relation_sql(lower_product({"value": expression}, {}))


class TypedLiteralSqlTests(unittest.TestCase):
    def test_text_canonical_units_lower_as_typed_literals(self) -> None:
        for expression, expected in TYPED_LITERALS:
            with self.subTest(literal=expected):
                self.assertEqual(_constant_sql(expression), _CONSTANT_SELECT.format(literal=expected))

    def test_scalar_units_keep_their_plain_literals(self) -> None:
        for expression, expected in (
            (literal(1), "1"),
            (literal(1.5), "1.5"),
            (literal(True), "TRUE"),
            (literal("text"), "'text'"),
            (literal(None, logical_type=NullableType(TIME)), "NULL"),
            (literal("2026-08-02"), "'2026-08-02'"),
        ):
            with self.subTest(literal=expected):
                self.assertEqual(_constant_sql(expression), _CONSTANT_SELECT.format(literal=expected))

    def test_a_temporal_fallback_is_typed_wherever_it_sits(self) -> None:
        selection = select_expression(wrap_expression(field_reference(
            source="input", path=("recorded_at",), logical_type=NullableType(TIME),
        )))
        sql = lower_relation_sql(lower_product(
            {"value": selection.default_to(time(9, 30)).expression.model},
            {"input": "source_relation"},
        ))
        self.assertEqual(
            sql,
            "SELECT COALESCE(\"t0\".\"recorded_at\", CAST('09:30:00' AS TIME))"
            " AS \"value\" FROM \"source_relation\" AS t0",
        )

    def test_arrays_of_text_canonical_items_lower_as_typed_array_literals(self) -> None:
        for expression, expected in TYPED_ARRAY_LITERALS:
            with self.subTest(literal=expected):
                self.assertEqual(_constant_sql(expression), _CONSTANT_SELECT.format(literal=expected))

    def test_arrays_of_the_json_units_keep_their_plain_literals(self) -> None:
        for expression, expected in UNTYPED_ARRAY_LITERALS:
            with self.subTest(literal=expected):
                self.assertEqual(_constant_sql(expression), _CONSTANT_SELECT.format(literal=expected))

    def test_an_array_fallback_is_typed_inside_coalesce(self) -> None:
        selection = select_expression(wrap_expression(field_reference(
            source="input", path=("recorded_on",), logical_type=NullableType(normalize_type(Array[date])),
        )))
        sql = lower_relation_sql(lower_product(
            {"value": selection.default_to([date(2026, 1, 1)]).expression.model},
            {"input": "source_relation"},
        ))
        self.assertEqual(
            sql,
            "SELECT COALESCE(\"t0\".\"recorded_on\", CAST(['2026-01-01'] AS DATE[]))"
            " AS \"value\" FROM \"source_relation\" AS t0",
        )

    def test_the_compiled_ir_carries_the_text_by_itself(self) -> None:
        for expression, _ in TYPED_LITERALS:
            with self.subTest(logical_type=str(expression.logical_type)):
                ir = expression_to_ir(expression)
                encoded = encode_expression_ir(ir)
                # The planner's dedup key and the blueprint document are plain json.dumps,
                # so the encoded literal must need no default hook of any kind.
                self.assertEqual(json.loads(json.dumps(encoded, sort_keys=True)), encoded)
                self.assertEqual(decode_expression_ir(encoded), ir)

    def test_duckdb_reads_each_literal_as_the_unit_its_node_declares(self) -> None:
        plan = lower_product({
            "a_date": literal(date(2026, 8, 2)),
            "a_time": literal(time(14, 20)),
            "a_timestamp": literal(datetime(2026, 8, 2, 14, 20, 0, 123456)),
            "a_uuid": literal(uuid.UUID("2f8a1c6e-9b4d-4a53-8f1a-6c0d2e4b8a91")),
            "a_string": literal("2026-08-02"),
        }, {})
        rows = duckdb.execute(lower_relation_sql(plan))
        self.assertEqual(
            [column[1].id for column in rows.description],
            ["date", "time", "timestamp", "uuid", "varchar"],
        )
        self.assertEqual(rows.fetchall(), [(
            date(2026, 8, 2), time(14, 20), datetime(2026, 8, 2, 14, 20, 0, 123456),
            uuid.UUID("2f8a1c6e-9b4d-4a53-8f1a-6c0d2e4b8a91"), "2026-08-02",
        )])

    def test_duckdb_types_each_array_literal_by_its_item_unit(self) -> None:
        cases: tuple[tuple[ExpressionNode, str], ...] = (
            (literal([date(2026, 1, 1)]), "DATE[]"),
            (literal([time(14, 20)]), "TIME[]"),
            (literal([datetime(2026, 8, 2, 14, 20)]), "TIMESTAMP[]"),
            (literal([uuid.UUID("2f8a1c6e-9b4d-4a53-8f1a-6c0d2e4b8a91")]), "UUID[]"),
            (literal([[date(2026, 1, 1)]]), "DATE[][]"),
            (literal([date(2026, 1, 1), None], logical_type=normalize_type(Array[date | None])), "DATE[]"),
            (literal([], logical_type=normalize_type(Array[date])), "DATE[]"),
            # The units that freeze as JSON need no cast: DuckDB already reads their array
            # as the type of its items.
            (literal([1, 2]), "INTEGER[]"),
            (literal(["2026-08-02"]), "VARCHAR[]"),
        )
        for expression, sql_type in cases:
            with self.subTest(sql_type=sql_type):
                row = duckdb.execute(
                    f'SELECT typeof("value") FROM ({_constant_sql(expression)})'
                ).fetchone()
                self.assertEqual(row, (sql_type,))

    def test_the_elementwise_cast_still_refuses_text_outside_the_unit(self) -> None:
        # The items stay text and one outer cast names the type of the array, so an item the
        # declared unit cannot hold is refused by the engine rather than reaching the scan
        # as a string. `literal` would have refused this value at authoring time already.
        node = LiteralExpression(value=("not-a-date",), logical_type=normalize_type(Array[date]))
        with self.assertRaisesRegex(duckdb.ConversionException, "invalid date field format"):
            duckdb.execute(_constant_sql(node))

    def test_a_typed_array_literal_merges_with_a_column_of_its_item_type(self) -> None:
        """COALESCE and UNION keep the column's DATE[] rather than widening to VARCHAR[]."""
        selection = select_expression(wrap_expression(field_reference(
            source="input", path=("days",), logical_type=NullableType(normalize_type(Array[date])),
        )))
        defaulted = lower_relation_sql(lower_product(
            {"value": selection.default_to([date(2026, 1, 2)]).expression.model},
            {"input": "source_relation"},
        ))
        constant = _constant_sql(literal([date(2026, 1, 2)]))
        connection = duckdb.connect()
        try:
            connection.execute("CREATE TABLE source_relation AS SELECT CAST(NULL AS DATE[]) AS days")
            self.assertEqual(
                connection.execute(f'SELECT typeof("value"), "value" FROM ({defaulted})').fetchone(),
                ("DATE[]", [date(2026, 1, 2)]),
            )
            self.assertEqual(
                connection.execute(
                    f"SELECT typeof(\"value\") FROM (SELECT * FROM ({constant})"
                    " UNION ALL SELECT days AS \"value\" FROM source_relation)"
                ).fetchall(),
                [("DATE[]",), ("DATE[]",)],
            )
            # Without the typed literal DuckDB has two array types to reconcile and refuses.
            with self.assertRaisesRegex(duckdb.BinderException, "Cannot mix values of type"):
                connection.execute("SELECT COALESCE(days, ['2026-01-02']) FROM source_relation")
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
