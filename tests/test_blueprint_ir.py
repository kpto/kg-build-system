from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import dataclass, replace
from pathlib import Path

from kg_build_system import (
    Annotation, Array, DataSourceConfig, Edge, Field,
    InputFormat, Node, Projection, ProjectionOptions, PropertySlot, Struct, Table,
    TableGroup, bind_source, create_blueprint, edge_binding, field, node_binding,
    projection_field, property,
)
from kg_build_system.compile import (
    blueprint_from_json, blueprint_json, decode_blueprint, validate_blueprint,
)
from kg_build_system.compile.models import BuildBlueprint
from kg_build_system.compile.compiler import _namespace_modules
from kg_build_system.expressions.ir import OperationExpressionIR, walk_expression_ir
from kg_build_system.table.ir import FieldIR, TableIR
from kg_build_system.types import STR
from kg_build_system.types.mapping import type_to_ir


@dataclass(frozen=True)
class Marker(Annotation):
    namespace = "blueprint_test"
    annotation_id = "marker"
    value: str


class EvidenceStruct(Struct):
    label: Field[str] = field(annotations=(Marker("field"),))


class EvidenceTable(Table):
    identifier: Field[str] = field()
    evidence: Field[Array[EvidenceStruct]] = field()


class UnusedTable(Table):
    identifier: Field[str] = field()


class BlueprintTableGroup(TableGroup):
    evidence = EvidenceTable
    unused = UnusedTable


class EvidenceProjection(Projection):
    options = ProjectionOptions(name="evidence_rows")
    identifier = projection_field(EvidenceTable.identifier)
    label = projection_field(
        EvidenceTable.evidence.expand().pick(lambda item: item.label)
    )


class EntityNode(Node):
    label: PropertySlot[str] = property()


class RelatedEdge(Edge[EntityNode, EntityNode]):
    label: PropertySlot[str] = property()


node = node_binding(
    target=EntityNode,
    build_key=EvidenceProjection.identifier,
    properties=EntityNode(label=EvidenceProjection.label),
    debug_name="entity",
)
edge = edge_binding(
    target=RelatedEdge,
    build_key=EvidenceProjection.identifier,
    source_build_key=EvidenceProjection.identifier,
    target_build_key=EvidenceProjection.identifier,
    properties=RelatedEdge(label=EvidenceProjection.label),
    debug_name="related",
)
source = bind_source(
    target=EvidenceTable,
    config=DataSourceConfig("evidence.parquet", format=InputFormat.PARQUET),
)


class BlueprintIRTests(unittest.TestCase):
    def blueprint(self) -> BuildBlueprint:
        return create_blueprint(
            bindings=(node, edge), sources=(source,), modules=(),
        )

    def test_blueprint_contains_complete_canonical_declarations(self) -> None:
        result = self.blueprint()
        self.assertEqual(result.schema_version, 4)
        self.assertEqual(tuple(item.module_id for item in result.modules), ("core",))
        self.assertEqual(tuple(item.name for item in result.structs), ("evidence",))
        self.assertEqual(tuple(item.name for item in result.tables), ("evidence",))
        self.assertEqual(tuple(item.name for item in result.projections), ("evidence_rows",))
        self.assertEqual({item.name for item in result.components}, {"entity", "related"})
        label = result.projections[0].fields[1].expression
        self.assertTrue(any(
            isinstance(item, OperationExpressionIR) and item.operator == "expand"
            for item in walk_expression_ir(label)
        ))

    def test_blueprint_prunes_unused_group_tables_and_sources(self) -> None:
        group_source = bind_source(
            target=BlueprintTableGroup,
            config=DataSourceConfig(
                "tables",
                format=InputFormat.PARQUET,
                layout="{table_name}/**/*.parquet",
            ),
        )

        result = create_blueprint(
            bindings=(node,), sources=(group_source,), modules=(),
        )

        self.assertEqual(tuple(item.name for item in result.tables), ("evidence",))
        self.assertEqual(
            tuple(item.name for item in result.projections), ("evidence_rows",)
        )
        self.assertEqual(tuple(item.name for item in result.structs), ("evidence",))
        self.assertEqual(tuple(item.table for item in result.sources), ("evidence",))
        self.assertEqual(result.sources[0].location, "tables/evidence/**/*.parquet")

    def test_json_codec_is_stable_and_round_trips_canonical_objects(self) -> None:
        result = self.blueprint()
        encoded = blueprint_json(result)
        decoded = blueprint_from_json(encoded)
        self.assertEqual(decoded, result)
        self.assertEqual(blueprint_json(decoded), encoded)
        document = json.loads(encoded)
        self.assertEqual(document["schema_version"], 4)
        expression = document["projections"][0]["fields"][1]["expression"]
        self.assertNotIn("rows", json.dumps(expression))
        self.assertNotIn("traversals", json.dumps(expression))

    def test_binding_symbols_are_deterministic(self) -> None:
        first = self.blueprint()
        second = self.blueprint()
        self.assertEqual(
            tuple(item.symbol_id for item in first.bindings),
            tuple(item.symbol_id for item in second.bindings),
        )

    def test_validator_rejects_unknown_expression_sources(self) -> None:
        result = self.blueprint()
        broken = replace(result, tables=(TableIR("table:other", "other", (FieldIR("id", type_to_ir(STR)),)),))
        with self.assertRaisesRegex(ValueError, "unknown logical source"):
            validate_blueprint(broken)

    def test_codec_rejects_other_schema_versions(self) -> None:
        raw = json.loads(blueprint_json(self.blueprint()))
        for stale in (3, 999):
            with self.subTest(schema_version=stale):
                raw["schema_version"] = stale
                with self.assertRaisesRegex(
                    ValueError, "unsupported blueprint schema version",
                ):
                    decode_blueprint(raw)

    def test_namespace_discovery_skips_non_importable_python_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "discovery_fixture"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "valid.py").write_text("VALUE = 1\n", encoding="utf-8")
            generated = package / "generated-output"
            generated.mkdir()
            (generated / "import_data.py").write_text(
                "raise AssertionError('must not be imported')\n", encoding="utf-8"
            )

            modules = _namespace_modules(package)

        self.assertEqual(
            {module.__name__ for module in modules},
            {"discovery_fixture", "discovery_fixture.valid"},
        )


class StructIdentityTests(unittest.TestCase):
    """Same-named structs across modules are display-duplicates, not clashes."""

    def test_same_struct_name_from_different_modules_is_allowed(self) -> None:
        from kg_build_system.compile.validation import validate_blueprint

        base = self.blueprint()
        original = base.structs[0]
        twin = replace(
            original,
            symbol_id="python:struct:other.module:EvidenceStruct",
            name=original.name,
        )
        widened = replace(base, structs=(*base.structs, twin))
        validate_blueprint(widened)

    def test_same_struct_name_same_module_is_rejected(self) -> None:
        from kg_build_system.compile.validation import validate_blueprint

        base = self.blueprint()
        original = base.structs[0]
        module = original.symbol_id.partition("python:struct:")[2].partition(":")[0]
        twin = replace(original, symbol_id=f"python:struct:{module}:OtherName")
        with self.assertRaises(ValueError):
            validate_blueprint(replace(base, structs=(*base.structs, twin)))

    def test_codec_round_trips_cross_module_struct_name_duplicates(self) -> None:
        base = self.blueprint()
        original = base.structs[0]
        twin = replace(original, symbol_id="python:struct:other.module:EvidenceStruct")
        widened = replace(base, structs=(*base.structs, twin))
        decoded = decode_blueprint(json.loads(blueprint_json(widened)))
        self.assertEqual(decoded.structs, widened.structs)

    def blueprint(self) -> BuildBlueprint:
        return create_blueprint(
            bindings=(node, edge), sources=(source,), modules=(),
        )


if __name__ == "__main__":
    unittest.main()
