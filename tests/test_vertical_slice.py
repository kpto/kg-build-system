import unittest
from pathlib import Path

from kg_build_system import (
    DataSourceConfig, Edge, Field, InputFormat, Node, NodeOptions, Projection,
    ProjectedField, PropertySlot, Struct, Table, TableGroup, TableGroupOptions,
    TableOptions, bind, bind_source, build, collection, compile_blueprint,
    create_blueprint, edge_binding, field, node_binding, projected_field,
    property, value,
)
from kg_build_system.modules import (
    CollapseExactDuplicatesModule, FileModule, FileModuleConfiguration,
    MergeCompatibleFactsModule, RejectConflictingNonNullValuesModule,
)


POST_PROCESSING = (
    CollapseExactDuplicatesModule(), RejectConflictingNonNullValuesModule(),
    MergeCompatibleFactsModule(),
)


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
    evidence: Field[list[EvidenceStruct]] = field()
    weight: Field[float] = field(name="score")


class ExpandedInputProjection(Projection):
    identifier: ProjectedField[str] = projected_field(InputTable.identifier)
    label: ProjectedField[str] = projected_field(InputTable.label)
    related: ProjectedField[str] = projected_field(collection.expand(InputTable.evidence.element.disease_id))
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


class AuthoringSurfaceTests(unittest.TestCase):
    def test_docstrings_and_explicit_options_define_metadata(self) -> None:
        self.assertEqual(ThingNode._component_name, "thing")
        self.assertEqual(ThingNode._metadata["description"], "A named test node.")
        self.assertEqual(RelatedEdge._metadata["description"], "A weighted self relationship.")
        self.assertIs(RelatedEdge._metadata["source"], ThingNode)
        self.assertIs(RelatedEdge._metadata["target"], ThingNode)

        blueprint = create_blueprint(
            bindings=[node_binding(target=ThingNode, build_key=InputTable.identifier, properties=ThingNode(label=bind(InputTable.label)))],
            modules=[*POST_PROCESSING, FileModule(FileModuleConfiguration("unused.jsonl"))],
        )
        self.assertEqual(blueprint.components[0].description, "A named test node.")

        class ExplicitNode(Node):
            """This description is overridden."""
            options = NodeOptions(description="The explicit description.")

        self.assertEqual(ExplicitNode._metadata["description"], "The explicit description.")

    def test_options_is_framework_metadata_and_trailing_underscore_escapes_it(self) -> None:
        self.assertEqual(TemplatedInputTable._fields["options_"].name, "options")
        self.assertEqual(OptionsNode._properties["options_"].name, "options")
        self.assertEqual(OptionsProjection.options_.path, ("options",))
        self.assertNotIn("options", TemplatedInputTable._fields)
        self.assertEqual(TemplatedInputTable._table_name, "templated_input")
        self.assertEqual(OptionsProjection._projection_name, "options")

    def test_table_groups_take_explicit_option_members_and_expand_sources(self) -> None:
        source = bind_source(
            target=ReleaseTableGroup,
            config=DataSourceConfig("fixtures", InputFormat.JSON, layout="{group_path}/{table_name}.json"),
        )
        blueprint = create_blueprint(
            bindings=[node_binding(target=ThingNode, build_key=InputTable.identifier, properties=ThingNode(label=bind(InputTable.label)))],
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
                node_binding(target=ThingNode, build_key=ExpandedInputProjection.identifier, properties=ThingNode(label=bind(ExpandedInputProjection.label))),
                node_binding(target=ThingNode, build_key=ExpandedInputProjection.related, properties=ThingNode(label=bind(ExpandedInputProjection.related))),
                edge_binding(
                    target=RelatedEdge,
                    build_key=value.deterministic_uuid(value.concat(ExpandedInputProjection.identifier, ExpandedInputProjection.related)),
                    source_build_key=ExpandedInputProjection.identifier,
                    target_build_key=ExpandedInputProjection.related,
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


if __name__ == "__main__":
    unittest.main()
