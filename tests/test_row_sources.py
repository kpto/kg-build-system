from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kg_build_system import (
    Array, DataSourceConfig, DerivedRowSource, Edge, EdgeValues, Field,
    InputFormat, Node, NodeValues, Projection, PropertySlot, RowSource, Shape,
    Struct, Table, TableGroup, TableGroupOptions, any_of, all_of, bind_source,
    build, compile, edge_binding, field, node_binding, projection_field,
    property,
)
from kg_build_system.compile import blueprint_from_json, blueprint_json
from kg_build_system.modules import (
    FileModule, FileModuleConfiguration, register_module,
)
from kg_build_system.expressions import BoolExpression
from kg_build_system.types import StructType, normalize_type


class Source(Table):
    kind: Field[str] = field()
    status: Field[str] = field()
    tags: Field[Array[str] | None] = field()


class Part(Struct):
    label: Field[str] = field()


class SourceView(Projection(Source.row_source())):
    kind = projection_field(Source.kind)


class Group(TableGroup):
    options = TableGroupOptions(members=(Source,))


class TargetNode(Node):
    label: PropertySlot[str] = property()


class Rel(Edge[TargetNode, TargetNode]):
    label: PropertySlot[str] = property()


class ShapeTests(unittest.TestCase):
    def test_table_and_projection_are_row_sources(self) -> None:
        self.assertTrue(issubclass(Source, Shape))
        self.assertTrue(issubclass(SourceView, Shape))
        self.assertTrue(issubclass(Source, RowSource))
        self.assertTrue(issubclass(SourceView, RowSource))
        self.assertFalse(issubclass(Part, RowSource))
        self.assertFalse(issubclass(Group, RowSource))
        self.assertIs(Source.shape, Source)
        self.assertTrue(issubclass(SourceView.shape, Shape))

    def test_shape_identity_is_the_declaration_pair(self) -> None:
        self.assertEqual(
            normalize_type(SourceView),
            StructType(SourceView.__module__, SourceView.__qualname__),
        )

    def test_where_is_shape_preserving_and_chains(self) -> None:
        active = Source.where(lambda source: any_of(
            source.kind.expression.equals("target"),
            source.kind.expression.equals("disease"),
        ))
        self.assertIsInstance(active, DerivedRowSource)
        self.assertIs(active.source, Source)
        self.assertTrue(issubclass(active.shape, Shape))
        self.assertEqual(len(active.filters), 1)

        strict = active.where(
            lambda source: source.status.expression.equals("active")
        )
        self.assertIs(strict.source, Source)
        self.assertEqual(len(strict.filters), 2)

    def test_projection_where_keeps_the_projection_shape(self) -> None:
        active = SourceView.where(
            lambda projection: projection.kind.expression.equals("target")
        )
        self.assertIs(active.source, SourceView)
        self.assertEqual(len(active.filters), 1)

    def test_empty_boolean_identities_are_boolean_expressions(self) -> None:
        self.assertIsInstance(any_of(), BoolExpression)
        self.assertIsInstance(all_of(), BoolExpression)

    def test_where_requires_a_callable_returning_a_boolean(self) -> None:
        with self.assertRaisesRegex(TypeError, "callable"):
            Source.where(Source.kind.expression.equals("target"))  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "BoolExpression"):
            Source.where(lambda source: source.kind.expression)  # type: ignore[arg-type]

    def test_edge_rows_binding_builds(self) -> None:
        active = Source.where(lambda source: source.kind.expression.equals("target"))
        binding = edge_binding(
            target=Rel,
            rows=active,
            bind=lambda row: EdgeValues(
                build_key=row.status,
                source_build_key=row.status,
                target_build_key=row.status,
                properties=Rel(label=row.kind),
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "rows.json"
            data.write_text(json.dumps([
                {"kind": "target", "status": "a", "tags": []},
                {"kind": "disease", "status": "b", "tags": []},
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
            rows = [
                json.loads(line)
                for line in (root / "output" / "graph.jsonl")
                .read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual([row["build_key"] for row in rows], ["a"])
        self.assertEqual(rows[0]["label"], "target")

    def test_blueprint_round_trip_preserves_row_sources(self) -> None:
        active = Source.where(lambda source: source.kind.expression.equals("target"))
        class ActiveTargets(active.projection_base(), active.shape):
            pass
        binding = node_binding(
            target=TargetNode,
            rows=ActiveTargets,
            bind=lambda row: NodeValues(
                build_key=row.status,
                properties=TargetNode(label=row.kind),
            ),
        )
        source = bind_source(
            target=Source,
            config=DataSourceConfig("rows.json", format=InputFormat.JSON),
        )
        from kg_build_system import create_blueprint

        blueprint = create_blueprint(
            bindings=(binding,), sources=(source,), modules=(),
        )
        decoded = blueprint_from_json(blueprint_json(blueprint))
        self.assertEqual(decoded, blueprint)

    def test_filtered_projection_and_rows_binding_build(self) -> None:
        active = Source.where(lambda source: source.kind.expression.equals("target"))

        class ActiveTargets(active.projection_base(), active.shape):
            pass

        class ActiveLabels(ActiveTargets.projection_base(), ActiveTargets.shape):
            status = projection_field(ActiveTargets.status)

        binding = node_binding(
            target=TargetNode,
            rows=ActiveLabels,
            bind=lambda row: NodeValues(
                build_key=row.status,
                properties=TargetNode(label=row.kind),
            ),
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "rows.json"
            data.write_text(json.dumps([
                {"kind": "target", "status": "a", "tags": []},
                {"kind": "disease", "status": "b", "tags": []},
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
            rows = [
                json.loads(line)
                for line in (root / "output" / "graph.jsonl")
                .read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual([row["build_key"] for row in rows], ["a"])
        self.assertEqual(rows[0]["label"], "target")


if __name__ == "__main__":
    unittest.main()
