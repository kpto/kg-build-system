from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kg_build_system import (
    AbstractEdge,
    AbstractNode,
    Array,
    DataSourceConfig,
    Edge,
    EdgeLabel,
    EdgeOptions,
    Field,
    InputFormat,
    Node,
    NodeLabel,
    NodeOptions,
    PropertySlot,
    Struct,
    Table,
    bind_source,
    build,
    compile,
    create_blueprint,
    edge_binding,
    field,
    node_binding,
    property,
)
from kg_build_system.binding.ir import NodeBindingIR
from kg_build_system.compile.models import BuildBlueprint
from kg_build_system.expressions import value_expression
from kg_build_system.expressions.mapping import expression_to_ir
from kg_build_system.modules import (
    CollapseExactDuplicatesModule,
    MetaGraphModule,
    register_module,
)
from kg_build_system.modules.targets.meta_graph import (
    MetaGraphModuleConfiguration,
)
from kg_build_system.modules.targets.meta_graph.ir import (
    MetaGraphDocumentIR,
    decode_meta_graph_instruction,
    encode_meta_graph_instruction,
)
from kg_build_system.modules.targets.meta_graph.topology import (
    component_entries,
    display_type,
    expand_type,
)
from kg_build_system.table.ir import FieldIR, StructIR
from kg_build_system.topology.ir import ComponentIR, PropertyIR
from kg_build_system.types import ArrayType, STR, normalize_type
from kg_build_system.types.ir import StructTypeIR
from kg_build_system.types.mapping import type_to_ir


class MetaInput(Table):
    identifier: Field[str] = field()
    other_identifier: Field[str] = field()
    name: Field[str] = field()
    summary: Field[str | None] = field()
    score: Field[float] = field()


class DocumentedAbstractNode(AbstractNode):
    """Category: every documented entity carries a summary."""

    options = NodeOptions(annotations=(NodeLabel("Documented"),))

    summary: PropertySlot[str | None] = property(description="Human-readable summary.")


class PersonNode(DocumentedAbstractNode, Node):
    name: PropertySlot[str] = property()


class TeamNode(DocumentedAbstractNode, Node):
    team_name: PropertySlot[str] = property()


class OrphanNode(DocumentedAbstractNode, Node):
    """Bound by nothing and named by no edge, so it is not effective."""

    extra: PropertySlot[str] = property()


class PersonRefNode(DocumentedAbstractNode, Node):
    """Never bound, but a bound edge declares it as an endpoint."""

    ref: PropertySlot[str] = property()


class IsolatedAbstractNode(AbstractNode):
    """A category with nothing bound beneath it."""

    marker: PropertySlot[str] = property()


class RelatedAbstractEdge(AbstractEdge[DocumentedAbstractNode, DocumentedAbstractNode]):
    """Category: relations between documented entities."""

    options = EdgeOptions(annotations=(EdgeLabel("RELATED"),))

    score: PropertySlot[float] = property()


class BelongsToEdge(RelatedAbstractEdge, Edge[PersonNode, TeamNode]):
    """A person belongs to a team."""


class RefersEdge(RelatedAbstractEdge, Edge[PersonNode, PersonRefNode]):
    """A person refers to a component that is never itself bound."""


person_binding = node_binding(
    target=PersonNode,
    build_key=MetaInput.identifier,
    properties=PersonNode(name=MetaInput.name, summary=MetaInput.summary),
)
team_binding = node_binding(
    target=TeamNode,
    build_key=MetaInput.other_identifier,
    properties=TeamNode(
        team_name=MetaInput.other_identifier, summary=MetaInput.summary,
    ),
)
belongs_binding = edge_binding(
    target=BelongsToEdge,
    build_key=MetaInput.identifier.expression.append("::").append(
        MetaInput.other_identifier.expression
    ),
    source_build_key=MetaInput.identifier,
    target_build_key=MetaInput.other_identifier,
    properties=BelongsToEdge(score=MetaInput.score),
)
refers_binding = edge_binding(
    target=RefersEdge,
    build_key=MetaInput.identifier.expression.append("##").append(
        MetaInput.other_identifier.expression
    ),
    source_build_key=MetaInput.identifier,
    target_build_key=MetaInput.other_identifier,
    properties=RefersEdge(score=MetaInput.score),
)

ALL_BINDINGS = (person_binding, team_binding, belongs_binding, refers_binding)


def _source(path: Path):
    return bind_source(
        target=MetaInput,
        config=DataSourceConfig(str(path), format=InputFormat.JSON),
    )


def _entries():
    """The effective topology for the fixture, without needing a workspace."""
    return component_entries(
        create_blueprint(bindings=ALL_BINDINGS, sources=(), modules=())
    )


def _entries_by_name():
    return {entry.name: entry for entry in _entries()}


def _data_rows() -> list[dict[str, object]]:
    """Two identical rows and one distinct row, so deduplication has work."""
    return [
        {"identifier": "p1", "other_identifier": "t1", "name": "Ada",
         "summary": None, "score": 1.5},
        {"identifier": "p1", "other_identifier": "t1", "name": "Ada",
         "summary": None, "score": 1.5},
        {"identifier": "p2", "other_identifier": "t1", "name": "Grace",
         "summary": "documented", "score": 2.5},
    ]


def _run(
    case: unittest.TestCase, *modules: object,
) -> tuple[Path, object, object, dict[str, object]]:
    """Compile and execute the fixture in a temporary directory."""
    directory = tempfile.TemporaryDirectory()
    case.addCleanup(directory.cleanup)
    root = Path(directory.name)
    data = root / "input.json"
    data.write_text(json.dumps(_data_rows()), encoding="utf-8")
    output = root / "output"
    contract = compile(
        bindings=ALL_BINDINGS,
        sources=(_source(data),),
        modules=tuple(modules),  # type: ignore[arg-type]
    )
    report = build(contract, output_directory=output)
    assert report.succeeded, report.unresolved_failures
    document = json.loads((output / "meta_graph.json").read_text(encoding="utf-8"))
    return output, contract, report, document


def _by_name(document: dict[str, object], kind: str) -> dict[str, dict[str, object]]:
    return {item["name"]: item for item in document[kind]}  # type: ignore[index]


class EffectiveTopologyTests(unittest.TestCase):
    def test_prunes_concrete_component_that_is_bound_by_nothing(self) -> None:
        self.assertNotIn("orphan", _entries_by_name())

    def test_prunes_category_with_nothing_effective_beneath_it(self) -> None:
        self.assertNotIn("isolated", _entries_by_name())

    def test_keeps_category_with_a_bound_child(self) -> None:
        documented = _entries_by_name()["documented"]
        self.assertTrue(documented.abstract)
        self.assertFalse(_entries_by_name()["person"].abstract)

    def test_keeps_endpoint_named_by_a_bound_edge_although_never_bound(self) -> None:
        self.assertIn("person_ref", _entries_by_name())

    def test_children_contain_only_effective_descendants_in_name_order(self) -> None:
        # `person_ref` is listed because a bound edge keeps it effective;
        # `orphan` is absent because nothing binds or names it.
        self.assertEqual(
            _entries_by_name()["documented"].children,
            ("person", "person_ref", "team"),
        )

    def test_parent_and_depth_follow_the_category_chain(self) -> None:
        entries = _entries_by_name()
        self.assertEqual(entries["documented"].parent, None)
        self.assertEqual(entries["documented"].depth, 0)
        self.assertEqual(entries["person"].parent, "documented")
        self.assertEqual(entries["person"].depth, 1)
        self.assertEqual(entries["belongs_to"].parent, "related")

    def test_hierarchy_uses_logical_names_while_symbol_ids_stay_for_debugging(self) -> None:
        person = _entries_by_name()["person"]
        self.assertEqual(person.parent, "documented")
        self.assertEqual(
            person.symbol_id, f"python:node:{PersonNode.__module__}:PersonNode",
        )

    def test_edge_reports_declared_endpoints_and_the_binding_resolution(self) -> None:
        belongs = _entries_by_name()["belongs_to"]
        assert belongs.endpoints is not None
        self.assertEqual(
            (belongs.endpoints.source, belongs.endpoints.target),
            ("person", "team"),
        )
        self.assertEqual(
            [(item.source_node, item.target_node) for item in belongs.bindings],
            [("person", "team")],
        )

    def test_label_comes_from_the_annotation_or_defaults_to_the_name(self) -> None:
        entries = _entries_by_name()
        self.assertEqual(entries["documented"].label, "Documented")
        self.assertEqual(entries["person"].label, "person")

    def test_descriptions_come_from_declarations(self) -> None:
        entries = _entries_by_name()
        self.assertEqual(
            entries["documented"].description,
            "Category: every documented entity carries a summary.",
        )
        self.assertEqual(
            entries["belongs_to"].description, "A person belongs to a team.",
        )
        summary = next(
            item for item in entries["documented"].properties if item.name == "summary"
        )
        self.assertEqual(summary.description, "Human-readable summary.")

    def test_category_properties_flow_to_concrete_components(self) -> None:
        person = _entries_by_name()["person"]
        self.assertEqual(
            [(item.name, item.type, item.nullable) for item in person.properties],
            [("summary", "str | None", True), ("name", "str", False)],
        )

    def test_graph_properties_are_scalar_so_types_stay_bounded(self) -> None:
        with self.assertRaisesRegex(TypeError, "must be a scalar"):
            class StructuredNode(Node):
                location: PropertySlot[Place | None] = property()  # type: ignore[valid-type]

        with self.assertRaisesRegex(TypeError, "must be a scalar"):
            class ArrayNode(Node):
                codes: PropertySlot[Array[str]] = property()  # type: ignore[valid-type]

    def test_step_waits_on_every_effective_graph_record_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "input.json"
            data.write_text(json.dumps(_data_rows()), encoding="utf-8")
            contract = compile(
                bindings=ALL_BINDINGS,
                sources=(_source(data),),
                modules=(register_module(MetaGraphModule),),
            )
            step = next(
                item for item in contract.workflow.steps
                if item.module_id == MetaGraphModule.ID
            )
            owner = {
                output.slot_id: producer.step_id
                for producer in contract.workflow.steps
                for output in producer.outputs
            }
            dependencies = {
                owner[connection.output_slot_id]
                for connection in contract.workflow.connections
                if connection.input_slot_id == step.inputs[0].slot_id
            }
            self.assertEqual(dependencies, {
                "core::aggregate.person",
                "core::aggregate.team",
                "core::aggregate.belongs_to",
                "core::aggregate.refers",
            })


class Place(Struct):
    city: Field[str] = field(description="Where it is.")
    room: Field[str | None] = field()


_STRUCT_KEY = (Place.__module__, "Place")


class LogicalTypeReportingTests(unittest.TestCase):
    """Struct expansion is exercised directly on the logical-type renderer."""

    def setUp(self) -> None:
        self.place_ir = StructIR(
            symbol_id=f"python:struct:{_STRUCT_KEY[0]}:{_STRUCT_KEY[1]}",
            name="place",
            fields=(
                FieldIR("city", type_to_ir(STR), "Where it is."),
                FieldIR("room", type_to_ir(normalize_type(str | None))),
            ),
        )
        self.structs = {_STRUCT_KEY: self.place_ir}

    def test_struct_members_are_expanded_from_the_blueprint(self) -> None:
        expanded = expand_type(type_to_ir(normalize_type(Place)), self.structs)
        self.assertEqual(expanded["kind"], "struct")
        self.assertEqual(expanded["declaration_name"], "place")
        self.assertEqual(
            [(item["name"], item["type"]) for item in expanded["members"]],
            [("city", "str"), ("room", "str | None")],
        )
        self.assertEqual(expanded["members"][0]["description"], "Where it is.")

    def test_display_type_matches_the_authoring_vocabulary(self) -> None:
        self.assertEqual(
            [display_type(type_to_ir(normalize_type(unit)))
             for unit in (bool, int, float, str, str | None)],
            ["bool", "int", "float", "str", "str | None"],
        )
        self.assertEqual(display_type(type_to_ir(ArrayType(STR))), "Array[str]")
        nested = ArrayType(normalize_type(str | None))
        self.assertEqual(
            display_type(type_to_ir(ArrayType(nested))), "Array[Array[str | None]]",
        )

    def test_a_recurring_struct_is_marked_rather_than_recursed(self) -> None:
        expanded = expand_type(
            StructTypeIR(*_STRUCT_KEY), self.structs, frozenset({_STRUCT_KEY}),
        )
        self.assertTrue(expanded["recursive"])
        self.assertNotIn("members", expanded)

    def test_an_undeclared_struct_is_reported_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "not declared in the blueprint"):
            expand_type(StructTypeIR("nowhere", "Missing"), self.structs)

    def test_a_struct_property_survives_the_payload_round_trip(self) -> None:
        component = ComponentIR(
            symbol_id=f"python:node:{Place.__module__}:PlaceNode",
            name="place_node",
            kind="node",
            properties=(PropertyIR(
                "place", type_to_ir(normalize_type(Place)), "The place.",
            ),),
        )
        blueprint = BuildBlueprint(
            structs=(self.place_ir,),
            tables=(),
            components=(component,),
            projections=(),
            bindings=(NodeBindingIR(
                "python:binding:m:place_binding",
                "place_node",
                expression_to_ir(value_expression("key").model),
                (),
            ),),
        )
        payload = MetaGraphDocumentIR(
            relative_path="meta_graph.json",
            components=component_entries(blueprint),
        )
        restored = decode_meta_graph_instruction(
            encode_meta_graph_instruction(payload)
        )
        reported = restored.components[0].properties[0]
        self.assertEqual(reported.type, "Place")
        self.assertFalse(reported.nullable)
        self.assertEqual(reported.description, "The place.")
        self.assertEqual(
            [item["name"] for item in reported.logical_type["members"]],
            ["city", "room"],
        )


class ExecutionTests(unittest.TestCase):
    def test_records_counts_and_hierarchy_roll_up(self) -> None:
        _output, _contract, _report, document = _run(self, register_module(MetaGraphModule))
        nodes = _by_name(document, "nodes")
        edges = _by_name(document, "edges")
        self.assertEqual(nodes["person"]["counts"]["records"], 3)
        self.assertEqual(nodes["team"]["counts"]["records"], 3)
        self.assertEqual(edges["belongs_to"]["counts"]["records"], 3)
        self.assertEqual(edges["refers"]["counts"]["records"], 3)
        self.assertEqual(nodes["documented"]["counts"]["records"], 0)
        self.assertEqual(nodes["documented"]["counts"]["inclusive_records"], 6)
        self.assertEqual(edges["related"]["counts"]["inclusive_records"], 6)
        self.assertEqual(nodes["person_ref"]["counts"]["records"], 0)

    def test_summary_totals_count_concrete_components_once(self) -> None:
        _output, _contract, _report, document = _run(self, register_module(MetaGraphModule))
        summary = document["summary"]
        self.assertEqual(summary["total_nodes"], 6)
        self.assertEqual(summary["total_edges"], 6)
        self.assertEqual(summary["node_components"], 4)
        self.assertEqual(summary["edge_components"], 3)
        self.assertEqual(summary["abstract_components"], 2)

    def test_counts_come_from_the_post_operator_artifact(self) -> None:
        _output, _contract, _report, document = _run(
            self,
            register_module(CollapseExactDuplicatesModule),
            register_module(MetaGraphModule),
        )
        nodes = _by_name(document, "nodes")
        edges = _by_name(document, "edges")
        # The duplicated input row collapses, while the third row's distinct
        # summary keeps its team record separate.
        self.assertEqual(nodes["person"]["counts"]["records"], 2)
        self.assertEqual(nodes["team"]["counts"]["records"], 2)
        self.assertEqual(edges["belongs_to"]["counts"]["records"], 2)
        self.assertEqual(edges["refers"]["counts"]["records"], 2)
        self.assertEqual(document["summary"]["total_nodes"], 4)
        self.assertEqual(document["summary"]["total_edges"], 4)

    def test_document_is_written_and_published(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "input.json"
            data.write_text(json.dumps(_data_rows()), encoding="utf-8")
            output = root / "nested" / "out"
            contract = compile(
                bindings=ALL_BINDINGS,
                sources=(_source(data),),
                modules=(register_module(
                    MetaGraphModule,
                    MetaGraphModuleConfiguration("meta/topology.json"),
                ),),
            )
            report = build(contract, output_directory=output)
            path = output / "meta" / "topology.json"
            self.assertTrue(path.is_file())
            published = {
                artifact.role.name: artifact.value
                for artifact in report.published_artifacts
            }
            self.assertIn("publication.meta_graph.meta_graph_document", published)
            summary = published["publication.meta_graph.meta_graph_document"]
            self.assertEqual(summary["location"], str(path))
            self.assertEqual(summary["total_nodes"], 6)

    def test_document_body_is_deterministic(self) -> None:
        _first_output, _contract, _report, first = _run(
            self, register_module(MetaGraphModule),
        )
        _second_output, _contract, _report, second = _run(
            self, register_module(MetaGraphModule),
        )

        def body(document: dict[str, object]) -> str:
            # Only the published location varies between two output directories.
            summary = dict(document["summary"])
            summary.pop("location")
            return json.dumps({**document, "summary": summary}, sort_keys=True)

        self.assertEqual(body(first), body(second))

    def test_payload_and_fingerprint_are_stable_for_identical_inputs(self) -> None:
        # The step payload feeds the workflow fingerprint, so it must be built
        # from sorted collections rather than iteration order.
        def fingerprint() -> tuple[str, object]:
            contract = compile(
                bindings=ALL_BINDINGS,
                sources=(_source(Path("input.json")),),
                modules=(register_module(MetaGraphModule),),
            )
            step = next(
                item for item in contract.workflow.steps
                if item.module_id == MetaGraphModule.ID
            )
            return contract.workflow_fingerprint, step.payload

        first_fingerprint, first_payload = fingerprint()
        second_fingerprint, second_payload = fingerprint()
        self.assertEqual(first_fingerprint, second_fingerprint)
        self.assertEqual(first_payload, second_payload)


class ConfigurationTests(unittest.TestCase):
    def test_default_relative_path(self) -> None:
        self.assertEqual(
            MetaGraphModuleConfiguration().relative_path, "meta_graph.json",
        )

    def test_rejects_absolute_escaping_and_blank_paths(self) -> None:
        absolute = str(Path(tempfile.gettempdir()) / "meta.json")
        for value in (absolute, "..", "a/../b.json", "  "):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    MetaGraphModuleConfiguration(value)

    def test_registration_supplies_the_default_configuration(self) -> None:
        self.assertEqual(
            register_module(MetaGraphModule).configuration,
            MetaGraphModuleConfiguration(),
        )


if __name__ == "__main__":
    unittest.main()
