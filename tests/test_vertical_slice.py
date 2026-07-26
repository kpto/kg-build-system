import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kg_build_system import DataSourceConfig, GraphComponent, bind_source, compile_build, compile_graph, edge, edge_binding, field, node, node_binding, property, provide, table
from kg_build_system.targets import FileTarget

@node()
class Thing(GraphComponent):
    label = property(name="label", nullable=False)
@edge(source=Thing, target=Thing)
class Related(GraphComponent):
    weight = property(name="weight")
@table(name="input")
class Input:
    id = field(name="target_id")
    label = field(name="target_symbol")
    related = field(name="disease_id")
    weight = field(name="score")

class VerticalSliceTests(unittest.TestCase):
    def test_compiles_and_writes_normalised_records(self):
        root = Path(__file__).parents[1]
        graph = compile_graph(bindings=[
            node_binding(target=Thing, build_key=Input.id, properties=Thing(label=Input.label)),
            edge_binding(target=Related, build_key=provide.value.deterministic_uuid(provide.value.concat(Input.id, Input.related)), source_build_key=Input.id, target_build_key=Input.related, properties=Related(weight=Input.weight)),
        ])
        with TemporaryDirectory() as directory:
            definition = compile_build(graph=graph, sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "association.csv")))], target=FileTarget(str(Path(directory) / "graph.jsonl")))
            self.assertIn("read_csv_auto", definition.sql)
            from kg_build_system import build
            report = build(definition)
            self.assertEqual((report.nodes, report.edges), (2, 2))

    def test_expand_is_visible_in_sql(self):
        graph = compile_graph(bindings=[node_binding(target=Thing, build_key=provide.collection.expand(Input.id), properties=Thing(label=Input.label))])
        definition = compile_build(graph=graph, sources=[bind_source(target=Input, config=DataSourceConfig("data.csv"))], target=FileTarget("out.jsonl"))
        self.assertIn("UNNEST", definition.sql)

if __name__ == "__main__": unittest.main()
