import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kg_build_system import (
    DataSourceConfig, ExpressionBinding, Field, GraphComponent, InputFormat,
    ProjectedField, PropertySlot, bind, bind_source, build, compile_build,
    compile_graph, edge, edge_binding, field, node, node_binding, projection,
    projected_field, property, provide, struct, table,
)
from kg_build_system.expressions import Expression, FieldPath
from kg_build_system.targets import FileTarget

@node()
class Thing(GraphComponent):
    label: PropertySlot[str] = property(name="label", nullable=False)

@edge(source=Thing, target=Thing)
class Related(GraphComponent):
    weight: PropertySlot[float] = property(name="weight")

@struct
class Evidence:
    disease_id: Field[str] = field(name="disease_id")
    labels: Field[list[str]] = field(name="labels")

@table(name="input")
class Input:
    identifier: Field[str] = field(name="target_id")
    label: Field[str] = field(name="target_symbol")
    evidence: Field[list[Evidence]] = field(name="evidence")
    weight: Field[float] = field(name="score")

@projection
class ExpandedInput:
    identifier: ProjectedField[str] = projected_field(Input.identifier)
    label: ProjectedField[str] = projected_field(Input.label)
    related: ProjectedField[str] = projected_field(provide.collection.expand(Input.evidence.element.disease_id))
    weight: ProjectedField[float] = projected_field(Input.weight)

class VerticalSliceTests(unittest.TestCase):
    def test_field_descriptor_and_bind_boundary(self) -> None:
        path = Input.label
        self.assertIsInstance(path, FieldPath)
        self.assertIsInstance(bind(path), ExpressionBinding)
        self.assertIsInstance(bind(path).expression, Expression)
        self.assertNotIsInstance(path, Expression)

    def test_projection_expands_and_writes_records(self) -> None:
        root = Path(__file__).parents[1]
        graph = compile_graph(bindings=[
            node_binding(target=Thing, build_key=ExpandedInput.identifier, properties=Thing(label=bind(ExpandedInput.label))),
            edge_binding(target=Related, build_key=provide.value.deterministic_uuid(provide.value.concat(ExpandedInput.identifier, ExpandedInput.related)), source_build_key=ExpandedInput.identifier, target_build_key=ExpandedInput.related, properties=Related(weight=bind(ExpandedInput.weight))),
        ], projections=[ExpandedInput])
        with TemporaryDirectory() as directory:
            definition = compile_build(graph=graph, sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "association.json"), format=InputFormat.JSON))], target=FileTarget(str(Path(directory) / "graph.jsonl")))
            self.assertIn("UNNEST", definition.sql)
            report = build(definition)
            self.assertEqual((report.nodes, report.edges), (2, 3))

    def test_unbound_graph_slot_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "must be assigned with bind"):
            compile_graph(bindings=[node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=Input.label))])

if __name__ == "__main__": unittest.main()
