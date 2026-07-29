import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kg_build_system import (
    DataSourceConfig, Declaration, GraphComponent, TableContract, bind_source,
    build, compile_build, compile_graph, edge, edge_binding, field, node,
    node_binding, projection, projected_field, property, provide, table,
)
from kg_build_system.specification import Specification
from kg_build_system.targets import FileTarget

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
    related: Declaration[str] = field(name="evidence")
    weight: Declaration[float] = field(name="score")

@projection
class ExpandedInput(Specification):
    id: Declaration[str] = projected_field(Input.id)
    label: Declaration[str] = projected_field(Input.label)
    evidence_item = provide.collection.expand(provide.value.cast(Input.related, "STRUCT(disease_id VARCHAR, labels VARCHAR[])[]"))
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
            definition = compile_build(graph=graph, sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "association.csv")))], target=FileTarget(str(Path(directory) / "graph.jsonl")))
            self.assertIn("UNNEST", definition.sql)
            self.assertEqual((build(definition).nodes, build(definition).edges), (2, 4))

    def test_collection_mapping_requires_expand(self) -> None:
        with self.assertRaisesRegex(TypeError, "maps a collection"):
            compile_graph(bindings=[node_binding(target=Thing, build_key=Input.id, properties=Thing(label=provide.value.cast(Input.related, "VARCHAR[]")))])

if __name__ == "__main__":
    unittest.main()
