import unittest
from dataclasses import dataclass
from pathlib import Path

from kg_build_system import (
    Annotation, BindingOptions, CollectionField, DataSourceConfig, Edge, Field, GraphComponent,
    GraphComponentOptions, InputFormat, Node, NodeOptions, Projection,
    ProjectionOptions, ProjectedField, PropertySlot, SourceBindingOptions,
    Struct, StructField, Table, TableGroup, TableGroupOptions, TableOptions, TableTemplate,
    TableTemplateOptions, ValueRef, bind, bind_source, build, collection, collection_field, compile_blueprint,
    create_blueprint, edge_binding, field, node_binding, projected_field, struct_field,
    property, value,
)
from kg_build_system.compile.models import ModuleDefinition, ModuleReference
from kg_build_system.data_types import Struct as DataStruct
from kg_build_system.expressions import Expression
from kg_build_system.workflow.interfaces import (
    CompilationContext, Module, ModuleCompilationResult, ModuleCompiler,
    ModuleRegistration, ModuleRegistrationConfiguration, WorkflowStepDraft,
)
from kg_build_system.modules import (
    CollapseExactDuplicatesModule, FileModule, FileModuleConfiguration,
    MergeCompatibleFactsModule, RejectConflictingNonNullValuesModule,
)


POST_PROCESSING = (
    CollapseExactDuplicatesModule(), RejectConflictingNonNullValuesModule(),
    MergeCompatibleFactsModule(),
)


@dataclass(frozen=True)
class PortableIndex(Annotation):
    namespace = "index"
    annotation_id = "index"

    unique: bool = False


@dataclass(frozen=True)
class ExampleModuleAnnotation(Annotation):
    namespace = "annotation_probe"
    annotation_id = "instruction"

    value: str = "enabled"


@dataclass(frozen=True)
class _ProbeConfiguration(ModuleRegistrationConfiguration):
    pass


class _ProbeCompiler:
    async def compile(self, context: CompilationContext[object]) -> ModuleCompilationResult:
        AnnotationProbeModule.seen_blueprint = context.blueprint
        return ModuleCompilationResult(
            ModuleDefinition(reference=ModuleReference(
                module_id=AnnotationProbeModule.ID,
                import_module=AnnotationProbeModule.__module__,
                class_qualname=AnnotationProbeModule.__qualname__,
                implementation_version="1",
                priority=context.priority,
            )),
            (),
        )


@dataclass(frozen=True)
class AnnotationProbeModule(Module, ModuleRegistration[_ProbeConfiguration]):
    configuration: _ProbeConfiguration = _ProbeConfiguration()
    ID = "annotation_probe"
    seen_blueprint = None

    @classmethod
    async def create_compiler(cls, context: object) -> ModuleCompiler:
        return _ProbeCompiler()

    @classmethod
    async def create_executor(cls, context: object):
        raise AssertionError("The probe module has no runtime steps")


class ThingNode(Node):
    """A named test node."""

    label: PropertySlot[str] = property()


class RelatedEdge(Edge[ThingNode, ThingNode]):
    """A weighted self relationship."""

    weight: PropertySlot[float] = property()


class EvidenceStruct(Struct):
    disease_id: Field[str] = field()


class InputTable(Table):
    identifier: Field[str] = field(name="target_id")
    label: Field[str] = field(name="target_symbol")
    evidence: CollectionField[EvidenceStruct] = collection_field()
    weight: Field[float] = field(name="score")


class NestedStruct(Struct):
    nested_field: Field[str] = field()


class StructuredInputTable(Table):
    a: Field[str] = field()
    b: StructField[NestedStruct] = struct_field()
    c: CollectionField[NestedStruct] = collection_field()


class ExpandedInputProjection(Projection):
    identifier: ProjectedField[str] = projected_field(InputTable.identifier)
    label: ProjectedField[str] = projected_field(InputTable.label)
    related: ProjectedField[str] = projected_field(collection.expand(InputTable.evidence.e.disease_id))
    weight: ProjectedField[float] = projected_field(InputTable.weight)


class SharedInputShape:
    options_: Field[str] = field()


class TemplatedInputTable(SharedInputShape, Table):
    identifier: Field[str] = field()


class OptionsProjection(Projection):
    options_: ProjectedField[str] = projected_field(TemplatedInputTable.options_)


class OptionsNode(Node):
    options_: PropertySlot[str] = property()


class ReferenceGroup(TableGroup):
    options = TableGroupOptions(members=(InputTable,))


class ReleaseTableGroup(TableGroup):
    """The test release hierarchy."""

    options = TableGroupOptions(members=(ReferenceGroup, TemplatedInputTable))


class AnnotatedTableTemplate(TableTemplate):
    options = TableTemplateOptions(annotations=[PortableIndex(unique=True)])
    code: Field[str] = field(annotations=[PortableIndex()])


class AnnotatedTable(AnnotatedTableTemplate, Table):
    pass


class AnnotatedGraphShape(GraphComponent):
    options = GraphComponentOptions(annotations=[PortableIndex()])
    code: PropertySlot[str] = property(annotations=[PortableIndex(unique=True)])


class AnnotatedNode(AnnotatedGraphShape, Node):
    options = NodeOptions(annotations=[ExampleModuleAnnotation("node")])


class AnnotatedProjection(Projection):
    options = ProjectionOptions(annotations=[PortableIndex()])
    code: ProjectedField[str] = projected_field(AnnotatedTable.code, annotations=[ExampleModuleAnnotation("projection_field")])


class AuthoringSurfaceTests(unittest.TestCase):
    def test_expressions_use_portable_value_refs(self) -> None:
        from kg_build_system import expressions
        from kg_build_system.table import TablePathValueRef

        reference = InputTable.identifier
        self.assertIsInstance(reference, ValueRef)
        self.assertIsInstance(reference, TablePathValueRef)
        self.assertIsInstance(reference, Field)
        self.assertIsInstance(InputTable.__dict__["identifier"], TablePathValueRef)
        self.assertIs(reference._metadata.table, InputTable)
        self.assertEqual(len(Field.__parameters__), 1)
        self.assertFalse(hasattr(expressions, "FieldPath"))
        self.assertEqual(value.literal(reference).op, "value_ref")

    def test_projected_fields_expose_value_references_not_source_expressions(self) -> None:
        reference = ExpandedInputProjection.related
        self.assertIsInstance(reference, ValueRef)
        self.assertNotIsInstance(reference, Expression)
        self.assertEqual(reference._metadata.table, ExpandedInputProjection)

    def test_struct_and_collection_fields_navigate_through_non_value_structs(self) -> None:
        self.assertTrue(issubclass(NestedStruct, DataStruct))
        self.assertNotIsInstance(StructuredInputTable.b.member, ValueRef)
        self.assertEqual(StructuredInputTable.b.member.nested_field._metadata.path, ("b", "nested_field"))
        self.assertEqual(StructuredInputTable.b.m.nested_field._metadata.path, ("b", "nested_field"))
        self.assertEqual(StructuredInputTable.c.element.nested_field._metadata.path, ("c", "nested_field"))
        self.assertEqual(StructuredInputTable.c.e.nested_field._metadata.path, ("c", "nested_field"))
        self.assertEqual(StructuredInputTable.c.element.nested_field._metadata.collection_paths, (("c",),))
        self.assertEqual(value.literal(StructuredInputTable.b).op, "value_ref")
        self.assertEqual(value.literal(StructuredInputTable.b.member.nested_field).op, "value_ref")

    def test_field_rejects_struct_types(self) -> None:
        with self.assertRaisesRegex(TypeError, "declare it with StructField"):
            class InvalidStructFieldTable(Table):
                nested: Field[NestedStruct] = field()

        with self.assertRaisesRegex(TypeError, "declare it with CollectionField"):
            class InvalidCollectionFieldTable(Table):
                nested: Field[list[NestedStruct]] = field()

    def test_declarations_and_literals_reject_unsupported_types(self) -> None:
        class ScalarCollectionTable(Table):
            labels: CollectionField[str] = collection_field()

        self.assertEqual(ScalarCollectionTable.labels.cardinality, "collection")
        with self.assertRaisesRegex(TypeError, "may not be a collection"):
            class InvalidScalarCollectionField(Table):
                labels: Field[list[str]] = field()

        with self.assertRaisesRegex(TypeError, "must be Scalar"):
            class InvalidValueTable(Table):
                payload: Field[dict[str, str]] = field()

        with self.assertRaisesRegex(TypeError, "may not be a collection"):
            class InvalidPropertyNode(Node):
                labels: PropertySlot[list[str]] = property()

        with self.assertRaisesRegex(TypeError, "literals must be Scalar"):
            value.literal({"unsupported": "map"})

    def test_value_expression_contracts_are_reflected_at_runtime(self) -> None:
        with self.assertRaises(TypeError):
            value.concat()  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            value.coalesce()  # type: ignore[call-arg]

        nullable = ValueRef[str | None](str | None)
        self.assertIs(value.coalesce(nullable, "fallback").type_hint, str)
        self.assertEqual(value.literal([["nested"], [None]]).args[0], [["nested"], [None]])

        self.assertIs(value.cast("1", "INTEGER").type_hint, int)
        self.assertEqual(value.cast(["1"], "VARCHAR[]").type_hint, list[str])
        with self.assertRaisesRegex(ValueError, "unsupported SQL cast type"):
            value.cast("1", "DECIMAL")  # type: ignore[arg-type]

    def test_graph_binding_arguments_require_explicit_bindings(self) -> None:
        properties = ThingNode(label=bind(InputTable.label))
        with self.assertRaisesRegex(TypeError, "build_key must be assigned with bind"):
            node_binding(target=ThingNode, build_key=InputTable.identifier, properties=properties)  # type: ignore[arg-type]

        with self.assertRaisesRegex(TypeError, "source_build_key must be assigned with bind"):
            edge_binding(
                target=RelatedEdge,
                build_key=bind("edge"),
                source_build_key=InputTable.identifier,  # type: ignore[arg-type]
                target_build_key=bind(InputTable.identifier),
                properties=RelatedEdge(weight=bind(InputTable.weight)),
            )

    def test_docstrings_and_explicit_options_define_metadata(self) -> None:
        self.assertEqual(ThingNode._component_name, "thing")
        self.assertEqual(ThingNode._metadata["description"], "A named test node.")
        self.assertEqual(RelatedEdge._metadata["description"], "A weighted self relationship.")
        self.assertIs(RelatedEdge._metadata["source"], ThingNode)
        self.assertIs(RelatedEdge._metadata["target"], ThingNode)

        blueprint = create_blueprint(
            bindings=[node_binding(target=ThingNode, build_key=bind(InputTable.identifier), properties=ThingNode(label=bind(InputTable.label)))],
            modules=[*POST_PROCESSING, FileModule(FileModuleConfiguration("unused.jsonl"))],
        )
        self.assertEqual(blueprint.components[0].description, "A named test node.")

        class ExplicitNode(Node):
            """This description is overridden."""
            options = NodeOptions(description="The explicit description.")

        self.assertEqual(ExplicitNode._metadata["description"], "The explicit description.")

    def test_options_is_framework_metadata_and_trailing_underscore_escapes_it(self) -> None:
        self.assertEqual(TemplatedInputTable._fields["options_"]._metadata.name, "options")
        self.assertEqual(OptionsNode._properties["options_"].name, "options")
        self.assertEqual(OptionsProjection.options_._metadata.path, ("options",))
        self.assertNotIn("options", TemplatedInputTable._fields)
        self.assertEqual(TemplatedInputTable._table_name, "templated_input")
        self.assertEqual(OptionsProjection._projection_name, "options")

    def test_table_groups_take_explicit_option_members_and_expand_sources(self) -> None:
        source = bind_source(
            target=ReleaseTableGroup,
            config=DataSourceConfig("fixtures", InputFormat.JSON, layout="{group_path}/{table_name}.json"),
        )
        blueprint = create_blueprint(
            bindings=[node_binding(target=ThingNode, build_key=bind(InputTable.identifier), properties=ThingNode(label=bind(InputTable.label)))],
            sources=[source], modules=[*POST_PROCESSING, FileModule(FileModuleConfiguration("unused.jsonl"))],
        )
        self.assertEqual(ReleaseTableGroup._data_metadata["description"], "The test release hierarchy.")
        self.assertEqual(
            tuple((item.table, item.location) for item in blueprint.sources),
            (
                ("input", "fixtures/release/reference_group/input.json"),
                ("templated_input", "fixtures/release/templated_input.json"),
            ),
        )

    def test_final_declarations_compile_and_execute(self) -> None:
        root = Path(__file__).parents[1]
        blueprint = create_blueprint(
            bindings=[
                node_binding(target=ThingNode, build_key=bind(ExpandedInputProjection.identifier), properties=ThingNode(label=bind(ExpandedInputProjection.label))),
                node_binding(target=ThingNode, build_key=bind(ExpandedInputProjection.related), properties=ThingNode(label=bind(ExpandedInputProjection.related))),
                edge_binding(
                    target=RelatedEdge,
                    build_key=bind(value.deterministic_uuid(value.concat(ExpandedInputProjection.identifier, ExpandedInputProjection.related))),
                    source_build_key=bind(ExpandedInputProjection.identifier),
                    target_build_key=bind(ExpandedInputProjection.related),
                    properties=RelatedEdge(weight=bind(ExpandedInputProjection.weight)),
                ),
            ],
            projections=[ExpandedInputProjection],
            sources=[bind_source(target=InputTable, config=DataSourceConfig(str(root / "demo" / "data" / "association.json"), InputFormat.JSON))],
            modules=[*POST_PROCESSING, FileModule(FileModuleConfiguration("unused.jsonl"))],
        )
        contract = compile_blueprint(blueprint=blueprint)
        self.assertTrue(any(step.step_id == "core::projection.expanded_input" for step in contract.workflow.steps))
        report = build(contract)
        self.assertTrue(report.succeeded)
        file_result = next(item.value for item in report.published_artifacts if item.role.name == "publication.file.write_result")
        self.assertEqual((file_result["nodes"], file_result["edges"]), (5, 3))

    def test_invalid_options_and_endpoints_are_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "Table.options"):
            class InvalidTable(Table):
                options = NodeOptions()

        with self.assertRaisesRegex(TypeError, "Edge must declare"):
            class InvalidEdge(Edge):
                pass

        with self.assertRaisesRegex(TypeError, "final Table"):
            class InvalidChild(InputTable):
                pass

    def test_annotations_are_serialised_additively_across_layers_and_visible_to_modules(self) -> None:
        source = bind_source(
            target=AnnotatedTable,
            config=DataSourceConfig("annotated.json", InputFormat.JSON),
            options=SourceBindingOptions(annotations=[ExampleModuleAnnotation("source")]),
        )
        blueprint = create_blueprint(
            bindings=[node_binding(
                target=AnnotatedNode,
                build_key=bind(AnnotatedProjection.code),
                properties=AnnotatedNode(code=bind(AnnotatedProjection.code)),
                options=BindingOptions(annotations=[ExampleModuleAnnotation("binding")]),
            )],
            projections=[AnnotatedProjection],
            sources=[source],
            modules=[AnnotationProbeModule(_ProbeConfiguration())],
        )
        component = blueprint.components[0]
        self.assertEqual(
            {(item.namespace, item.annotation_id, item.arguments.get("value")) for item in component.annotations},
            {("index", "index", None), ("annotation_probe", "instruction", "node")},
        )
        self.assertEqual(component.properties[0].annotations[0].arguments, {"unique": True})
        self.assertEqual(blueprint.projections[0].field_annotations["code"][0].annotation_id, "instruction")
        self.assertEqual(blueprint.bindings[0].annotations[0].arguments, {"value": "binding"})
        self.assertEqual(len(blueprint.sources[0].annotations), 2)
        self.assertEqual(blueprint.sources[0].annotations[1].arguments, {"value": "source"})
        self.assertEqual(blueprint.bindings[0].build_key.annotations[0].annotation_id, "instruction")
        round_tripped = type(blueprint).model_validate_json(blueprint.model_dump_json())
        self.assertEqual(round_tripped.components[0].annotations, component.annotations)

        compile_blueprint(blueprint=blueprint)
        self.assertIs(AnnotationProbeModule.seen_blueprint, blueprint)
        assert AnnotationProbeModule.seen_blueprint is not None
        self.assertEqual(AnnotationProbeModule.seen_blueprint.components[0].annotations[0].namespace, "index")


if __name__ == "__main__":
    unittest.main()
