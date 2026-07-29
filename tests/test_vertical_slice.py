import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kg_build_system import (
    DataSourceConfig, Declaration, GraphComponent, InputFormat, TableContract, bind_source,
    build, compile_build, compile_graph, edge, edge_binding, field, node,
    node_binding, projection, projected_field, property, provide, struct, table,
)
from kg_build_system.specification import Specification
from kg_build_system.specification.type_shapes import type_shape
from kg_build_system.targets import FileTarget
from kg_build_system.expressions import Expression, FieldPath

@node()
class Thing(GraphComponent):
    label: Declaration[str] = property(name="label", nullable=False)

@edge(source=Thing, target=Thing)
class Related(GraphComponent):
    weight: Declaration[float] = property(name="weight")

@table(name="input")
class Input(TableContract):
    id: Declaration[str] = field(name="target_id")
    label: Declaration[str] = field(name="target_symbol")
    related: Declaration[list[object]] = field(name="evidence")
    weight: Declaration[float] = field(name="score")

@struct
class OptionalEvidence(TableContract):
    labels: Declaration[list[str | None]] = field(name="labels")

@table(name="optional_input")
class OptionalInput(TableContract):
    identifier: Declaration[str | None] = field(name="identifier")
    evidence: Declaration[OptionalEvidence | None] = field(name="evidence")

@projection
class ExpandedInput(Specification):
    id: Declaration[str] = projected_field(Input.id)
    label: Declaration[str] = projected_field(Input.label)
    evidence_item = provide.collection.expand(Input.related)
    related: Declaration[str] = projected_field(provide.value.struct_field(evidence_item, "disease_id", as_type=str))
    evidence_label: Declaration[str] = projected_field(provide.collection.expand(provide.value.struct_field(evidence_item, "labels", as_type=list[str])))
    weight: Declaration[float] = projected_field(Input.weight)

class VerticalSliceTests(unittest.TestCase):
    def test_projection_expands_and_writes_normalised_records(self) -> None:
        root = Path(__file__).parents[1]
        graph = compile_graph(bindings=[
            node_binding(target=Thing, build_key=ExpandedInput.id, properties=Thing(label=ExpandedInput.label)),
            edge_binding(target=Related, build_key=provide.value.deterministic_uuid(provide.value.concat(ExpandedInput.id, ExpandedInput.related, ExpandedInput.evidence_label)), source_build_key=ExpandedInput.id, target_build_key=ExpandedInput.related, properties=Related(weight=ExpandedInput.weight)),
        ], projections=[ExpandedInput])
        with TemporaryDirectory() as directory:
            definition = compile_build(graph=graph, sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "association.json"), format=InputFormat.JSON))], target=FileTarget(str(Path(directory) / "graph.jsonl")))
            self.assertIn("UNNEST", definition.sql)
            self.assertEqual((build(definition).nodes, build(definition).edges), (2, 4))

    def test_collection_mapping_requires_expand(self) -> None:
        with self.assertRaisesRegex(TypeError, "maps a collection"):
            compile_graph(bindings=[node_binding(target=Thing, build_key=Input.id, properties=Thing(label=Input.related))])

    def test_required_property_rejects_nullable_expression(self) -> None:
        with self.assertRaisesRegex(TypeError, "required but expression may be null"):
            compile_graph(bindings=[node_binding(target=Thing, build_key=Input.id, properties=Thing(label=OptionalInput.identifier))])

    def test_required_key_rejects_nullable_expression(self) -> None:
        with self.assertRaisesRegex(TypeError, "build key may not be nullable"):
            compile_graph(bindings=[node_binding(target=Thing, build_key=OptionalInput.identifier, properties=Thing(label=Input.label))])

    def test_optional_struct_navigation_preserves_collection_item_nullability(self) -> None:
        path = OptionalInput.evidence.labels
        self.assertEqual(path.cardinality, "collection")
        self.assertEqual(path.type_hint, list[str | None] | None)
        self.assertTrue(type_shape(path.type_hint).nullable)

    def test_provide_normalizes_a_field_path_without_changing_its_type(self) -> None:
        path = Input.label
        expression = provide(path)
        self.assertIsInstance(path, FieldPath)
        self.assertNotIsInstance(path, Expression)
        self.assertIsInstance(expression, Expression)
        self.assertEqual(expression.op, "field")
        binding = node_binding(target=Thing, build_key=Input.id, properties=Thing(label=Input.label))
        self.assertIsInstance(binding.build_key, Expression)
        self.assertIsInstance(binding.properties._values["label"], Expression)

if __name__ == "__main__":
    unittest.main()
