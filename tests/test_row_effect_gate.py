from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kg_build_system import (
    Array, DataSourceConfig, Field, InputFormat, Node, NodeValues, PropertySlot,
    Struct, Table, bind_source, build, compile, field, node_binding, property,
)
from kg_build_system.modules import FileModule, FileModuleConfiguration, register_module


class Detail(Struct):
    code: Field[str] = field()


class Source(Table):
    kind: Field[str] = field()
    status: Field[str | None] = field()
    tags: Field[Array[str] | None] = field()
    detail: Field[Detail | None] = field()


class Item(Node):
    label: PropertySlot[str] = property()


class RowEffectGateTests(unittest.TestCase):
    def _build(self, binding):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "rows.json"
            data.write_text(json.dumps([
                {"kind": "a", "status": "x", "tags": ["p", "q"], "detail": {"code": "c1"}},
                {"kind": "b", "status": None, "tags": None, "detail": None},
                {"kind": "c", "status": "y", "tags": ["q"], "detail": {"code": "c2"}},
            ]), encoding="utf-8")
            source = bind_source(
                target=Source,
                config=DataSourceConfig(str(data), format=InputFormat.JSON),
            )
            contract = compile(
                bindings=(binding,),
                sources=(source,),
                modules=(register_module(
                    FileModule, FileModuleConfiguration("graph.jsonl"),
                ),),
            )
            report = build(contract, output_directory=root / "output")
            self.assertTrue(report.succeeded)
            return [
                json.loads(line)
                for line in (root / "output" / "graph.jsonl")
                .read_text(encoding="utf-8").splitlines()
            ]

    def test_drop_null_is_the_gated_presence_filter(self) -> None:
        binding = node_binding(
            target=Item,
            rows=Source,
            bind=lambda row: NodeValues(
                build_key=row.status.alter_rows().drop_null(),
                properties=Item(label=row.kind),
            ),
        )
        rows = self._build(binding)
        self.assertEqual([row["build_key"] for row in rows], ["x", "y"])

    def test_expand_is_gated_and_returns_one_row_per_element(self) -> None:
        binding = node_binding(
            target=Item,
            rows=Source,
            bind=lambda row: NodeValues(
                build_key=row.kind.expression.append("::").append(
                    row.tags.alter_rows().drop_null().alter_rows().expand().expression
                ),
                properties=Item(label=row.kind),
            ),
        )
        rows = self._build(binding)
        self.assertEqual(
            sorted(row["build_key"] for row in rows),
            ["a::p", "a::q", "c::q"],
        )

    def test_drop_if_filters_by_a_value_predicate(self) -> None:
        binding = node_binding(
            target=Item,
            rows=Source,
            bind=lambda row: NodeValues(
                build_key=row.kind,
                properties=Item(label=row.kind),
            ),
        )
        # Replace the binding above with one whose row source carries the filter.
        binding = node_binding(
            target=Item,
            rows=Source.where(
                lambda row: row.status.alter_rows().drop_null().expression.equals("x")
            ),
            bind=lambda row: NodeValues(build_key=row.kind, properties=Item(label=row.kind)),
        )
        rows = self._build(binding)
        self.assertEqual([row["build_key"] for row in rows], ["a"])

    def test_extract_replaces_pick(self) -> None:
        binding = node_binding(
            target=Item,
            rows=Source,
            bind=lambda row: NodeValues(
                build_key=row.detail.alter_rows().drop_null().extract(lambda d: d.code),
                properties=Item(label=row.kind),
            ),
        )
        rows = self._build(binding)
        self.assertEqual(sorted(row["build_key"] for row in rows), ["c1", "c2"])

    def test_legacy_names_remain_aliases(self) -> None:
        selection = Source.status
        self.assertIs(selection.where_present.__func__, selection.drop_null.__func__)
        self.assertIs(Source.detail.pick.__func__, Source.detail.extract.__func__)
        self.assertIs(Source.tags.distinct.__func__, Source.tags.unique.__func__)
        self.assertIs(Source.tags.join.__func__, Source.tags.concat.__func__)


if __name__ == "__main__":
    unittest.main()


class ArrayNavigationTests(unittest.TestCase):
    def _build(self, binding):
        return RowEffectGateTests()._build(binding)

    def test_at_is_zero_based_and_nullable_on_missing_index(self) -> None:
        binding = node_binding(
            target=Item,
            rows=Source,
            bind=lambda row: NodeValues(
                build_key=row.kind.expression.append("::").append(
                    row.tags.alter_rows().drop_null().at(0).alter_rows().drop_null().expression
                ),
                properties=Item(label=row.kind),
            ),
        )
        rows = self._build(binding)
        self.assertEqual(sorted(row["build_key"] for row in rows), ["a::p", "c::q"])

    def test_slice_keeps_the_array_value(self) -> None:
        binding = node_binding(
            target=Item,
            rows=Source,
            bind=lambda row: NodeValues(
                build_key=row.kind.expression.append("::").append(
                    row.tags.alter_rows().drop_null().slice(0, 2).concat("|").expression
                ),
                properties=Item(label=row.kind),
            ),
        )
        rows = self._build(binding)
        self.assertEqual(sorted(row["build_key"] for row in rows), ["a::p|q", "c::q"])
