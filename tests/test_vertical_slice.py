import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kg_build_system import (
    BuildBlueprint, DataSourceConfig, ExpressionBinding, Field, GraphComponent, InputFormat,
    ProjectedField, PropertySlot, bind, bind_source, build, compile_blueprint,
    create_blueprint, edge, edge_binding, field, node, node_binding, projection,
    projected_field, property, struct, table, value, collection,
)
from kg_build_system.expressions import Expression, FieldPath
from kg_build_system.modules import CollapseExactDuplicatesModule, FileModule, FileModuleConfiguration, MergeCompatibleFactsModule, RejectConflictingNonNullValuesConfiguration, RejectConflictingNonNullValuesModule
from kg_build_system.modules.core import CoreArtifactRoles
from kg_build_system.compile.models import ArtifactRole

POST_PROCESSING = [CollapseExactDuplicatesModule(), RejectConflictingNonNullValuesModule(), MergeCompatibleFactsModule()]

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
    def test_core_artifact_roles_are_a_stable_extension_vocabulary(self) -> None:
        role = CoreArtifactRoles.graph_records("node", "Thing")
        self.assertEqual(role, ArtifactRole(namespace="core", name="graph.node.Thing"))
        identity = CoreArtifactRoles.graph_record_identity(role)
        self.assertIsNotNone(identity)
        assert identity is not None
        self.assertEqual((identity.kind, identity.component), ("node", "Thing"))
        self.assertTrue(CoreArtifactRoles.is_publication(CoreArtifactRoles.published("example", "result")))

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
        ], projections=[ExpandedInput], sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "association.json"), format=InputFormat.JSON))], modules=[*POST_PROCESSING, FileModule(FileModuleConfiguration(str(root / "unused.jsonl")))])
        with TemporaryDirectory() as directory:
            contract = compile_blueprint(blueprint=blueprint)
            self.assertTrue(any("UNNEST" in str(step.payload) for step in contract.workflow.steps))
            self.assertTrue(any(step.step_id.startswith("core::binding.") for step in contract.workflow.steps))
            report = build(contract)
            self.assertEqual((report.nodes, report.edges), (5, 3))
            self.assertTrue(report.succeeded)
            self.assertTrue(report.published_artifacts)
            self.assertFalse(any(artifact.role == CoreArtifactRoles.published("reject_conflicting_non_null_values", "report") for artifact in report.published_artifacts))
            self.assertEqual(report.metrics["graph.nodes"], 5)
            self.assertEqual(report.metrics["graph.edges"], 3)

    def test_unbound_graph_slot_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "must be assigned with bind"):
            create_blueprint(bindings=[node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=Input.label))], modules=[*POST_PROCESSING, FileModule(FileModuleConfiguration("unused.jsonl"))])

    def test_each_binding_has_an_isolated_execution_plan(self) -> None:
        root = Path(__file__).parents[1]
        blueprint = create_blueprint(bindings=[
            node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=bind(Input.label))),
            node_binding(target=Thing, build_key=ExpandedInput.related, properties=Thing(label=bind(ExpandedInput.related))),
            edge_binding(target=Related, build_key=value.deterministic_uuid(ExpandedInput.related), source_build_key=ExpandedInput.identifier, target_build_key=ExpandedInput.related, properties=Related(weight=bind(ExpandedInput.weight))),
        ], projections=[ExpandedInput], sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "association.json"), format=InputFormat.JSON))], modules=[*POST_PROCESSING, FileModule(FileModuleConfiguration(str(root / "unused.jsonl")))])
        with TemporaryDirectory() as directory:
            contract = compile_blueprint(blueprint=blueprint)
            binding_steps = [step for step in contract.workflow.steps if step.step_id.startswith("core::binding.")]
            self.assertEqual(len(binding_steps), 3)
            self.assertNotIn("UNNEST", str(binding_steps[0].payload))
            self.assertIn("UNNEST", str(binding_steps[1].payload))
            report = build(contract)
            self.assertEqual((report.nodes, report.edges), (5, 3))

    def test_edge_endpoint_keys_contribute_source_requirements(self) -> None:
        root = Path(__file__).parents[1]
        blueprint = create_blueprint(bindings=[
            edge_binding(target=Related, build_key=Input.identifier, source_build_key=Input.identifier, target_build_key=Endpoint.identifier, properties=Related(weight=bind(Input.weight))),
        ], sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "association.json"), format=InputFormat.JSON))], modules=[*POST_PROCESSING, FileModule(FileModuleConfiguration(str(root / "unused.jsonl")))])
        with self.assertRaisesRegex(ValueError, "Endpoint"):
            compile_blueprint(blueprint=blueprint)

    def test_conflicting_non_null_facts_fail_in_duckdb_normalisation(self) -> None:
        root = Path(__file__).parents[1]
        blueprint = create_blueprint(bindings=[
            node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=bind(Input.label))),
            node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=bind(value.literal("conflict")))),
        ], sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "association.json"), format=InputFormat.JSON))], modules=[*POST_PROCESSING, FileModule(FileModuleConfiguration(str(root / "unused.jsonl")))])
        with TemporaryDirectory() as directory:
            contract = compile_blueprint(blueprint=blueprint)
            report = build(contract)
            self.assertEqual(len(report.unresolved_failures), 1)
            self.assertFalse(report.succeeded)
            self.assertTrue(all(artifact.role.name.startswith("publication.") for artifact in report.published_artifacts))
            validation_report = next(artifact for artifact in report.published_artifacts if artifact.role == CoreArtifactRoles.published("reject_conflicting_non_null_values", "report"))
            self.assertGreaterEqual(len(validation_report.value.findings), 1)
            report_only_blueprint = create_blueprint(bindings=[
                node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=bind(Input.label))),
                node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=bind(value.literal("conflict")))),
            ], sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "association.json"), format=InputFormat.JSON))], modules=[
                CollapseExactDuplicatesModule(),
                RejectConflictingNonNullValuesModule(RejectConflictingNonNullValuesConfiguration(fail_on_error=False)), MergeCompatibleFactsModule(),
                FileModule(FileModuleConfiguration(str(root / "unused.jsonl"))),
            ])
            report_only = build(compile_blueprint(blueprint=report_only_blueprint))
            self.assertEqual(report_only.unresolved_failures, ())
            self.assertTrue(any(artifact.role == CoreArtifactRoles.published("reject_conflicting_non_null_values", "report") for artifact in report_only.published_artifacts))

    def test_contract_records_file_module(self) -> None:
        root = Path(__file__).parents[1]
        blueprint = create_blueprint(
            bindings=[node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=bind(Input.label)))],
            sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "association.json"), format=InputFormat.JSON))],
            modules=[*POST_PROCESSING, FileModule(FileModuleConfiguration("compiled-override.jsonl"))],
        )
        self.assertEqual({module.module_id for module in blueprint.modules}, {
            "collapse_exact_duplicates", "merge_compatible_facts",
            "reject_conflicting_non_null_values", "file",
        })
        contract = compile_blueprint(blueprint=BuildBlueprint.model_validate_json(blueprint.model_dump_json()))
        file_module = next(module for module in contract.workflow.modules if module.reference.module_id == "file")
        self.assertEqual(file_module.reference.class_qualname, "FileModule")
        self.assertTrue({"collapse_exact_duplicates", "merge_compatible_facts", "reject_conflicting_non_null_values"} <= {module.reference.module_id for module in contract.workflow.modules})
        file_step = next(step for step in contract.workflow.steps if step.module_id == "file")
        self.assertEqual(file_module.reference.configuration, {"location": "compiled-override.jsonl"})
        termination = next(step for step in contract.workflow.steps if step.step_id == "core::publish.result")
        self.assertEqual(termination.outputs, ())
        self.assertTrue(any(connection.input_slot_id == "core::publish.result.publications" for connection in contract.workflow.connections))

    def test_module_priority_orders_steps_and_selects_the_latest_record_producer(self) -> None:
        root = Path(__file__).parents[1]
        def contract_for(modules: list[object]):
            blueprint = create_blueprint(
                bindings=[node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=bind(Input.label)))],
                sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "association.json"), format=InputFormat.JSON))],
                modules=modules,
            )
            return compile_blueprint(blueprint=blueprint)

        validation_then_merge = contract_for([
            CollapseExactDuplicatesModule(), RejectConflictingNonNullValuesModule(),
            MergeCompatibleFactsModule(), FileModule(FileModuleConfiguration("unused.jsonl")),
        ])
        merge_then_validation = contract_for([
            CollapseExactDuplicatesModule(), MergeCompatibleFactsModule(),
            RejectConflictingNonNullValuesModule(), FileModule(FileModuleConfiguration("unused.jsonl")),
        ])

        def file_producer(contract: object) -> str:
            workflow = contract.workflow  # type: ignore[attr-defined]
            connection = next(item for item in workflow.connections if item.input_slot_id == "file::write.records")
            return next(step.module_id for step in workflow.steps if any(output.slot_id == connection.output_slot_id for output in step.outputs))

        self.assertEqual(file_producer(validation_then_merge), "merge_compatible_facts")
        self.assertEqual(file_producer(merge_then_validation), "reject_conflicting_non_null_values")
        step_modules = [step.module_id for step in validation_then_merge.workflow.steps if step.module_id != "core"]
        self.assertLess(step_modules.index("reject_conflicting_non_null_values"), step_modules.index("merge_compatible_facts"))
        self.assertEqual(
            [module.reference.priority for module in validation_then_merge.workflow.modules],
            list(range(len(validation_then_merge.workflow.modules))),
        )

if __name__ == "__main__": unittest.main()
