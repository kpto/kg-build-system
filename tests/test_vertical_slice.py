import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kg_build_system import (
    DataSourceConfig, ExpressionBinding, Field, GraphComponent, InputFormat,
    ProjectedField, PropertySlot, bind, bind_source, build, compile_blueprint,
    create_blueprint, edge, edge_binding, field, node, node_binding, projection,
    projected_field, property, struct, table, value, collection, normalise_graph,
    collapse_exact_duplicates, merge_compatible_facts, reject_conflicting_non_null_values, validate_edge_endpoints,
)
from kg_build_system.expressions import Expression, FieldPath
from kg_build_system.targets import FileTarget

POST_PROCESSING = normalise_graph(
    collapse_exact_duplicates(),
    merge_compatible_facts(),
    reject_conflicting_non_null_values(),
    validate_edge_endpoints(),
)

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

@table(name="endpoint")
class Endpoint:
    identifier: Field[str] = field(name="target_id")

@projection
class ExpandedInput:
    identifier: ProjectedField[str] = projected_field(Input.identifier)
    label: ProjectedField[str] = projected_field(Input.label)
    related: ProjectedField[str] = projected_field(collection.expand(Input.evidence.element.disease_id))
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
        blueprint = create_blueprint(bindings=[
            node_binding(target=Thing, build_key=ExpandedInput.identifier, properties=Thing(label=bind(ExpandedInput.label))),
            node_binding(target=Thing, build_key=ExpandedInput.related, properties=Thing(label=bind(ExpandedInput.related))),
            edge_binding(target=Related, build_key=value.deterministic_uuid(value.concat(ExpandedInput.identifier, ExpandedInput.related)), source_build_key=ExpandedInput.identifier, target_build_key=ExpandedInput.related, properties=Related(weight=bind(ExpandedInput.weight))),
        ], projections=[ExpandedInput], sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "association.json"), format=InputFormat.JSON))], post_processing=POST_PROCESSING)
        with TemporaryDirectory() as directory:
            contract = compile_blueprint(blueprint=blueprint, target=FileTarget(str(Path(directory) / "graph.jsonl")))
            self.assertTrue(any("UNNEST" in plan.sql for plan in contract.plans))
            self.assertTrue(contract.debug_symbols)
            report = build(contract)
            self.assertEqual((report.nodes, report.edges), (5, 3))

    def test_unbound_graph_slot_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "must be assigned with bind"):
            create_blueprint(bindings=[node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=Input.label))], post_processing=POST_PROCESSING)

    def test_each_binding_has_an_isolated_execution_plan(self) -> None:
        root = Path(__file__).parents[1]
        blueprint = create_blueprint(bindings=[
            node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=bind(Input.label))),
            node_binding(target=Thing, build_key=ExpandedInput.related, properties=Thing(label=bind(ExpandedInput.related))),
            edge_binding(target=Related, build_key=value.deterministic_uuid(ExpandedInput.related), source_build_key=ExpandedInput.identifier, target_build_key=ExpandedInput.related, properties=Related(weight=bind(ExpandedInput.weight))),
        ], projections=[ExpandedInput], sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "association.json"), format=InputFormat.JSON))], post_processing=POST_PROCESSING)
        with TemporaryDirectory() as directory:
            contract = compile_blueprint(blueprint=blueprint, target=FileTarget(str(Path(directory) / "graph.jsonl")))
            self.assertEqual(len(contract.plans), 3)
            self.assertNotIn("UNNEST", contract.plans[0].sql)
            self.assertIn("UNNEST", contract.plans[1].sql)
            report = build(contract)
            self.assertEqual((report.nodes, report.edges, report.diagnostics), (5, 3, ()))

    def test_edge_endpoint_keys_contribute_source_requirements(self) -> None:
        root = Path(__file__).parents[1]
        blueprint = create_blueprint(bindings=[
            edge_binding(target=Related, build_key=Input.identifier, source_build_key=Input.identifier, target_build_key=Endpoint.identifier, properties=Related(weight=bind(Input.weight))),
        ], sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "association.json"), format=InputFormat.JSON))], post_processing=POST_PROCESSING)
        with self.assertRaisesRegex(ValueError, "Endpoint"):
            compile_blueprint(blueprint=blueprint, target=FileTarget(str(root / "temporary.jsonl")))

    def test_conflicting_non_null_facts_fail_in_duckdb_normalisation(self) -> None:
        root = Path(__file__).parents[1]
        blueprint = create_blueprint(bindings=[
            node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=bind(Input.label))),
            node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=bind(value.literal("conflict")))),
        ], sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "association.json"), format=InputFormat.JSON))], post_processing=POST_PROCESSING)
        with TemporaryDirectory() as directory:
            contract = compile_blueprint(blueprint=blueprint, target=FileTarget(str(Path(directory) / "graph.jsonl")))
            with self.assertRaisesRegex(ValueError, "non-null values for label"):
                build(contract)

if __name__ == "__main__": unittest.main()
