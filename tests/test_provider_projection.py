from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kg_build_system import (
    DataSourceConfig, Field, InputFormat, Node, NodeValues, Projection, PropertySlot,
    Table, bind_source, build, compile, computed_field, field, node_binding, property,
)
from kg_build_system.modules import FileModule, FileModuleConfiguration, register_module
from kg_build_system.table.interfaces import RelationRowSource


class Source(Table):
    id: Field[str] = field()
    kind: Field[str] = field()


class Pinned(Projection(Source.row_source())):
    id = computed_field(Source.id)
    kind = computed_field(Source.kind)


class Item(Node):
    label: PropertySlot[str] = property()


class ProviderProjectionTests(unittest.TestCase):
    def test_table_and_projection_provide_row_sources(self) -> None:
        table_source = Source.row_source()
        self.assertIsInstance(table_source, RelationRowSource)
        self.assertIs(table_source.shape, Source)
        self.assertIs(table_source.source, Source)

        projection_source = Pinned.row_source()
        self.assertIsInstance(projection_source, RelationRowSource)
        self.assertIs(projection_source.source, Pinned)
        self.assertIs(projection_source.shape, Pinned.shape)

    def test_pinned_projection_records_its_row_source(self) -> None:
        self.assertEqual(Pinned._projection_row_source, Source.row_source())
        self.assertEqual(
            Pinned._projection_row_source.source,
            Source,
        )

    def test_binding_consumes_row_source_directly(self) -> None:
        binding = node_binding(
            target=Item,
            rows=Source.row_source(),
            bind=lambda row: NodeValues(build_key=row.id.alter_rows().drop_null(), properties=Item(label=row.kind.alter_rows().drop_null())),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "rows.json").write_text(json.dumps([{"id": "a", "kind": "x"}]))
            source = bind_source(
                target=Source,
                config=DataSourceConfig(str(root / "rows.json"), format=InputFormat.JSON),
            )
            contract = compile(
                bindings=(binding,),
                sources=(source,),
                modules=(register_module(
                    FileModule, FileModuleConfiguration("graph.jsonl"),
                ),),
            )
            report = build(contract, output_directory=root / "out")
            self.assertTrue(report.succeeded)
            rows = [json.loads(line) for line in (root / "out" / "graph.jsonl").read_text().splitlines()]
        self.assertEqual([row["build_key"] for row in rows], ["a"])

    def test_bind_and_where_receive_a_shape_instance(self) -> None:
        seen: list[bool] = []

        def predicate(row: Source):
            seen.append(type(row) is Source)
            return row.kind.alter_rows().drop_null().expression.equals("x")

        Source.where(predicate)
        self.assertEqual(seen, [True])

        def bind(row: Source):
            seen.append(type(row) is Source)
            return NodeValues(build_key=row.id.alter_rows().drop_null(), properties=Item(label=row.kind.alter_rows().drop_null()))

        node_binding(target=Item, rows=Source.row_source(), bind=bind)
        self.assertEqual(seen, [True, True])

    def test_row_source_where_preserves_shape(self) -> None:
        filtered = Source.row_source().where(
            lambda row: row.kind.alter_rows().drop_null().expression.equals("x")
        )
        self.assertEqual(len(filtered.filters), 1)
        self.assertIs(filtered.shape, Source)
        self.assertIs(filtered.source, Source)


if __name__ == "__main__":
    unittest.main()
