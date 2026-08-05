import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kg_build_system import (
    BuildBlueprint, DataSourceConfig, ExpressionBinding, Field, GraphComponent, InputFormat,
    ProjectedField, PropertySlot, bind, bind_source, build, compile_blueprint,
    component_template, create_blueprint, edge, edge_binding, field, node, node_binding, projection,
    projected_field, property, struct, table, table_group, table_template, value, collection, WorkflowArtifactRoles, include,
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


class ImplicitDetails:
    code: Field[str] = field(name="code")


class ImplicitTableShape:
    identifier: Field[str] = field(name="identifier")
    details: Field[ImplicitDetails] = field(name="details")


@table_template(name="explicit_shape", description="Reusable input shape")
class ExplicitTableShape:
    label: Field[str] = field(name="label")


@table(name="templated_input")
class TemplatedInput(ImplicitTableShape, ExplicitTableShape):
    pass


class ImplicitGraphShape(GraphComponent):
    label: PropertySlot[str] = property(name="label", nullable=False)


@component_template(description="Reusable graph component shape")
class ExplicitGraphShape(GraphComponent):
    description: PropertySlot[str | None] = property(name="description")


@node()
class TemplatedThing(ImplicitGraphShape, ExplicitGraphShape):
    pass


@table(name="grouped_input")
class GroupedInput:
    identifier: Field[str] = field(name="identifier")


@table(name="grouped_endpoint")
class GroupedEndpoint:
    identifier: Field[str] = field(name="identifier")


@table_group(name="nested")
class NestedInputs:
    input = include(GroupedInput)


@table_group(name="release")
class GroupedInputs:
    nested = include(NestedInputs)
    endpoint = include(GroupedEndpoint)


@table_group()
class AutoNamedTableGroup:
    input = include(GroupedInput)


@node()
class TargetNode(GraphComponent):
    displayName: PropertySlot[str] = property(nullable=False)


@edge(source=TargetNode, target=TargetNode)
class RelatedToEdge(GraphComponent):
    pass


@table()
class CamelCaseTable:
    targetID: Field[str] = field()


@projection
class CamelCaseProjection:
    targetID: ProjectedField[str] = projected_field(CamelCaseTable.targetID)

class VerticalSliceTests(unittest.TestCase):
    def test_auto_names_use_snake_case_and_kind_suffixes(self) -> None:
        self.assertEqual(TargetNode._component_name, "target")
        self.assertEqual(RelatedToEdge._component_name, "related_to")
        self.assertEqual(CamelCaseTable._table_name, "camel_case")
        self.assertEqual(CamelCaseTable._fields["targetID"].name, "target_id")
        self.assertEqual(CamelCaseProjection._projection_name, "camel_case")
        self.assertEqual(CamelCaseProjection.targetID.path, ("target_id",))
        self.assertEqual(AutoNamedTableGroup._table_group_name, "auto_named")

        @table(name="external_input")
        class ExplicitNameTable:
            targetID: Field[str] = field(name="target_identifier")

        @projection(name="external_projection")
        class ExplicitNameProjection:
            targetID: ProjectedField[str] = projected_field(ExplicitNameTable.targetID)

        self.assertEqual(ExplicitNameTable._table_name, "external_input")
        self.assertEqual(ExplicitNameTable._fields["targetID"].name, "target_identifier")
        self.assertEqual(ExplicitNameProjection._projection_name, "external_projection")

    def test_declaration_name_cannot_be_only_its_suffix(self) -> None:
        with self.assertRaisesRegex(ValueError, "no name"):
            @node()
            class Node(GraphComponent):
                pass

    def test_table_groups_expand_nested_catalog_paths_and_sources(self) -> None:
        grouped_source = bind_source(
            target=GroupedInputs,
            config=DataSourceConfig("fixtures", format=InputFormat.JSON, layout="{group_path}/{table_name}.json"),
        )
        self.assertEqual(
            (grouped_source.group, grouped_source.config.location),  # type: ignore[union-attr]
            (GroupedInputs, "fixtures"),
        )
        blueprint = create_blueprint(
            bindings=[node_binding(target=Thing, build_key=GroupedInput.identifier, properties=Thing(label=bind(GroupedInput.identifier)))],
            sources=[grouped_source],
            modules=[*POST_PROCESSING, FileModule(FileModuleConfiguration("unused.jsonl"))],
        )
        self.assertEqual(
            tuple((source.table, source.location) for source in blueprint.sources),
            (
                ("grouped_input", "fixtures/release/nested/grouped_input.json"),
                ("grouped_endpoint", "fixtures/release/grouped_endpoint.json"),
            ),
        )

    def test_implicit_and_explicit_data_templates_are_resolved_by_final_tables(self) -> None:
        self.assertEqual(TemplatedInput._data_declaration_kind, "table")
        self.assertEqual(ExplicitTableShape._data_declaration_kind, "table_template")
        self.assertEqual(ExplicitTableShape._data_metadata["description"], "Reusable input shape")
        self.assertEqual(TemplatedInput._data_metadata["description"], "Reusable input shape")
        self.assertEqual(TemplatedInput.identifier.type_hint, str)
        self.assertEqual(TemplatedInput.label.type_hint, str)
        self.assertEqual(TemplatedInput.details.code.path, ("details", "code"))
        self.assertEqual(TemplatedInput.details.code.table, TemplatedInput)

    def test_explicit_struct_is_optional_but_can_carry_metadata(self) -> None:
        @struct(name="annotated_details", description="A reusable nested record")
        class AnnotatedDetails:
            code: Field[str] = field(name="code")

        @table(name="annotated_input")
        class AnnotatedInput:
            details: Field[AnnotatedDetails] = field(name="details")

        self.assertEqual(AnnotatedDetails._data_declaration_kind, "struct")
        self.assertEqual(AnnotatedDetails._data_metadata["description"], "A reusable nested record")
        self.assertEqual(AnnotatedInput.details.code.path, ("details", "code"))

    def test_final_table_and_component_inheritance_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "final @table"):
            @table(name="invalid_table")
            class InvalidTable(Input):
                pass

        with self.assertRaisesRegex(TypeError, "final graph component"):
            @node()
            class InvalidComponent(Thing):
                pass

    def test_templates_are_not_executable_inputs(self) -> None:
        with self.assertRaisesRegex(TypeError, "final @table"):
            bind_source(target=ExplicitTableShape, config=DataSourceConfig("unused.json"))

        with self.assertRaisesRegex(TypeError, "final @table"):
            @projection
            class InvalidProjection:
                label = projected_field(ExplicitTableShape.label)

        with self.assertRaisesRegex(TypeError, "final @node or @edge"):
            create_blueprint(
                bindings=[node_binding(target=ImplicitGraphShape, build_key=TemplatedInput.identifier, properties=TemplatedThing(label=bind(TemplatedInput.label), description=bind(value.literal(None))))],
                sources=[bind_source(target=TemplatedInput, config=DataSourceConfig("unused.json"))],
                modules=[*POST_PROCESSING, FileModule(FileModuleConfiguration("unused.jsonl"))],
            )

        with self.assertRaisesRegex(TypeError, "final @table inputs"):
            create_blueprint(
                bindings=[node_binding(target=TemplatedThing, build_key=ExplicitTableShape.label, properties=TemplatedThing(label=bind(ExplicitTableShape.label), description=bind(value.literal(None))))],
                modules=[*POST_PROCESSING, FileModule(FileModuleConfiguration("unused.jsonl"))],
            )

    def test_implicit_and_explicit_component_templates_are_inherited(self) -> None:
        self.assertEqual(TemplatedThing._kind, "node")
        self.assertEqual(set(TemplatedThing._properties), {"label", "description"})
        self.assertEqual(TemplatedThing._metadata["description"], "Reusable graph component shape")
        instance = TemplatedThing(label=bind(value.literal("thing")), description=bind(value.literal(None)))
        self.assertIsInstance(instance.label, ExpressionBinding)

    def test_core_artifact_roles_are_a_stable_extension_vocabulary(self) -> None:
        role = CoreArtifactRoles.graph_records("node", "Thing")
        self.assertEqual(role, ArtifactRole(namespace="core", name="graph.node.Thing"))
        identity = CoreArtifactRoles.graph_record_identity(role)
        self.assertIsNotNone(identity)
        assert identity is not None
        self.assertEqual((identity.kind, identity.component), ("node", "Thing"))
        publication = WorkflowArtifactRoles.published("example", "result")
        self.assertEqual(publication, ArtifactRole(namespace="workflow", name="publication.example.result"))
        self.assertTrue(WorkflowArtifactRoles.is_published(publication))
        self.assertEqual(CoreArtifactRoles.table("input"), ArtifactRole(namespace="core", name="data.table.input"))
        self.assertEqual(CoreArtifactRoles.projection("expanded_input"), ArtifactRole(namespace="core", name="data.projection.expanded_input"))

    def test_field_descriptor_and_bind_boundary(self) -> None:
        path = Input.label
        self.assertIsInstance(path, FieldPath)
        self.assertIsInstance(bind(path), ExpressionBinding)
        self.assertIsInstance(bind(path).expression, Expression)
        self.assertNotIsInstance(path, Expression)

    def _file_result(self, report: object) -> dict[str, object]:
        published = report.published_artifacts  # type: ignore[attr-defined]
        artifact = next(item for item in published if item.role == WorkflowArtifactRoles.published("file", "write_result"))
        assert isinstance(artifact.value, dict)
        return artifact.value

    def test_projection_expands_and_writes_records(self) -> None:
        root = Path(__file__).parents[1]
        blueprint = create_blueprint(bindings=[
            node_binding(target=Thing, build_key=ExpandedInput.identifier, properties=Thing(label=bind(ExpandedInput.label))),
            node_binding(target=Thing, build_key=ExpandedInput.related, properties=Thing(label=bind(ExpandedInput.related))),
            edge_binding(target=Related, build_key=value.deterministic_uuid(value.concat(ExpandedInput.identifier, ExpandedInput.related)), source_build_key=ExpandedInput.identifier, target_build_key=ExpandedInput.related, properties=Related(weight=bind(ExpandedInput.weight))),
        ], projections=[ExpandedInput], sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "data_files" / "association.json"), format=InputFormat.JSON))], modules=[*POST_PROCESSING, FileModule(FileModuleConfiguration(str(root / "unused.jsonl")))])
        with TemporaryDirectory() as directory:
            contract = compile_blueprint(blueprint=blueprint)
            self.assertTrue(any("UNNEST" in str(step.payload) for step in contract.workflow.steps))
            self.assertTrue(any(step.step_id.startswith("core::binding.") for step in contract.workflow.steps))
            self.assertTrue(any(step.step_id == "core::table.input" for step in contract.workflow.steps))
            self.assertTrue(any(step.step_id == "core::projection.expanded_input" for step in contract.workflow.steps))
            projection_step = next(step for step in contract.workflow.steps if step.step_id == "core::projection.expanded_input")
            binding_step = next(step for step in contract.workflow.steps if step.step_id.startswith("core::binding."))
            self.assertIn('"kg_table_0"', str(projection_step.payload))
            self.assertIn('"kg_projection_0"', str(binding_step.payload))
            self.assertNotIn("read_json_auto", str(binding_step.payload))
            self.assertTrue(any(
                connection.input_slot_id == binding_step.inputs[0].slot_id
                and connection.output_slot_id == "core::projection.expanded_input.output"
                for connection in contract.workflow.connections
            ))
            report = build(contract)
            self.assertEqual((self._file_result(report)["nodes"], self._file_result(report)["edges"]), (5, 3))
            self.assertTrue(report.succeeded)
            self.assertTrue(report.published_artifacts)
            self.assertFalse(any(artifact.role == WorkflowArtifactRoles.published("reject_conflicting_non_null_values", "report") for artifact in report.published_artifacts))

    def test_unbound_graph_slot_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "must be assigned with bind"):
            create_blueprint(bindings=[node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=Input.label))], modules=[*POST_PROCESSING, FileModule(FileModuleConfiguration("unused.jsonl"))])

    def test_each_binding_has_an_isolated_execution_plan(self) -> None:
        root = Path(__file__).parents[1]
        blueprint = create_blueprint(bindings=[
            node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=bind(Input.label))),
            node_binding(target=Thing, build_key=ExpandedInput.related, properties=Thing(label=bind(ExpandedInput.related))),
            edge_binding(target=Related, build_key=value.deterministic_uuid(ExpandedInput.related), source_build_key=ExpandedInput.identifier, target_build_key=ExpandedInput.related, properties=Related(weight=bind(ExpandedInput.weight))),
        ], projections=[ExpandedInput], sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "data_files" / "association.json"), format=InputFormat.JSON))], modules=[*POST_PROCESSING, FileModule(FileModuleConfiguration(str(root / "unused.jsonl")))])
        with TemporaryDirectory() as directory:
            contract = compile_blueprint(blueprint=blueprint)
            binding_steps = [step for step in contract.workflow.steps if step.step_id.startswith("core::binding.")]
            self.assertEqual(len(binding_steps), 3)
            self.assertNotIn("UNNEST", str(binding_steps[0].payload))
            self.assertNotIn("UNNEST", str(binding_steps[1].payload))
            projection_step = next(step for step in contract.workflow.steps if step.step_id == "core::projection.expanded_input")
            self.assertIn("UNNEST", str(projection_step.payload))
            report = build(contract)
            self.assertEqual((self._file_result(report)["nodes"], self._file_result(report)["edges"]), (5, 3))

    def test_edge_endpoint_keys_contribute_source_requirements(self) -> None:
        root = Path(__file__).parents[1]
        blueprint = create_blueprint(bindings=[
            edge_binding(target=Related, build_key=Input.identifier, source_build_key=Input.identifier, target_build_key=Endpoint.identifier, properties=Related(weight=bind(Input.weight))),
        ], sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "data_files" / "association.json"), format=InputFormat.JSON))], modules=[*POST_PROCESSING, FileModule(FileModuleConfiguration(str(root / "unused.jsonl")))])
        with self.assertRaisesRegex(ValueError, "endpoint"):
            compile_blueprint(blueprint=blueprint)

    def test_conflicting_non_null_facts_fail_in_duckdb_normalisation(self) -> None:
        root = Path(__file__).parents[1]
        blueprint = create_blueprint(bindings=[
            node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=bind(Input.label))),
            node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=bind(value.literal("conflict")))),
        ], sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "data_files" / "association.json"), format=InputFormat.JSON))], modules=[*POST_PROCESSING, FileModule(FileModuleConfiguration(str(root / "unused.jsonl")))])
        with TemporaryDirectory() as directory:
            contract = compile_blueprint(blueprint=blueprint)
            report = build(contract)
            self.assertEqual(len(report.unresolved_failures), 1)
            self.assertFalse(report.succeeded)
            self.assertTrue(all(artifact.role.namespace == "workflow" and artifact.role.name.startswith("publication.") for artifact in report.published_artifacts))
            validation_report = next(artifact for artifact in report.published_artifacts if artifact.role == WorkflowArtifactRoles.published("reject_conflicting_non_null_values", "report"))
            self.assertGreaterEqual(len(validation_report.value.findings), 1)
            report_only_blueprint = create_blueprint(bindings=[
                node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=bind(Input.label))),
                node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=bind(value.literal("conflict")))),
        ], sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "data_files" / "association.json"), format=InputFormat.JSON))], modules=[
                CollapseExactDuplicatesModule(),
                RejectConflictingNonNullValuesModule(RejectConflictingNonNullValuesConfiguration(fail_on_error=False)), MergeCompatibleFactsModule(),
                FileModule(FileModuleConfiguration(str(root / "unused.jsonl"))),
            ])
            report_only = build(compile_blueprint(blueprint=report_only_blueprint))
            self.assertEqual(report_only.unresolved_failures, ())
            self.assertTrue(any(artifact.role == WorkflowArtifactRoles.published("reject_conflicting_non_null_values", "report") for artifact in report_only.published_artifacts))

    def test_unhandled_step_exception_becomes_a_failed_outcome(self) -> None:
        root = Path(__file__).parents[1]
        blueprint = create_blueprint(bindings=[
            node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=bind(Input.label))),
        ], sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "missing.json"), format=InputFormat.JSON))], modules=[
            *POST_PROCESSING,
            FileModule(FileModuleConfiguration("unused.jsonl")),
        ])
        report = build(compile_blueprint(blueprint=blueprint))
        self.assertFalse(report.succeeded)
        self.assertEqual(len(report.unresolved_failures), 1)
        failure = report.unresolved_failures[0]
        self.assertEqual(failure.module_id, "core")
        self.assertEqual(failure.step_id, "core::table.input")
        self.assertIsNotNone(failure.exception_type)

    def test_contract_records_file_module(self) -> None:
        root = Path(__file__).parents[1]
        blueprint = create_blueprint(
            bindings=[node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=bind(Input.label)))],
            sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "data_files" / "association.json"), format=InputFormat.JSON))],
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
        self.assertFalse(any(step.step_id == "core::publish.result" for step in contract.workflow.steps))

    def test_module_priority_orders_steps_and_selects_the_latest_record_producer(self) -> None:
        root = Path(__file__).parents[1]
        def contract_for(modules: list[object]):
            blueprint = create_blueprint(
                bindings=[node_binding(target=Thing, build_key=Input.identifier, properties=Thing(label=bind(Input.label)))],
                sources=[bind_source(target=Input, config=DataSourceConfig(str(root / "demo" / "data_files" / "association.json"), format=InputFormat.JSON))],
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
