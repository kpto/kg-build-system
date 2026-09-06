from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from uuid import UUID

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
from kg_build_system.binding.models import Binding
from kg_build_system.compile.models import BuildBlueprint
from kg_build_system.expressions import value_expression
from kg_build_system.expressions.mapping import expression_to_ir
from kg_build_system.modules import (
    CollapseExactDuplicatesModule,
    MetaGraphModule,
    Neo4jModule,
    RejectConflictingNonNullValuesModule,
    RejectConflictingNonNullValuesConfiguration,
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
from kg_build_system.modules.targets.meta_graph.module import (
    _canonical_example_value,
    _example_order_key,
)
from kg_build_system.modules.targets.meta_graph.render import render
from kg_build_system.modules.targets.meta_graph.topology import (
    component_entries,
    display_type,
    expand_type,
)
from kg_build_system.table.ir import FieldIR, StructIR
from kg_build_system.topology.ir import ComponentIR, PropertyIR
from kg_build_system.types import (
    ArrayType,
    Date,
    STR,
    Time,
    Timestamp,
    UnitType,
    normalize_type,
    Uuid,
)
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
    case: unittest.TestCase, *modules: object, bindings: Iterable[Binding] = ALL_BINDINGS,
) -> tuple[Path, object, object, dict[str, object]]:
    """Compile and execute the fixture in a temporary directory."""
    directory = tempfile.TemporaryDirectory()
    case.addCleanup(directory.cleanup)
    root = Path(directory.name)
    data = root / "input.json"
    data.write_text(json.dumps(_data_rows()), encoding="utf-8")
    output = root / "output"
    contract = compile(
        bindings=bindings,
        sources=(_source(data),),
        modules=tuple(modules),  # type: ignore[arg-type]
    )
    report = build(contract, output_directory=output)
    assert report.succeeded, report.unresolved_failures
    document = json.loads((output / "meta_graph.json").read_text(encoding="utf-8"))
    return output, contract, report, document


def _by_name(document: dict[str, object], kind: str) -> dict[str, dict[str, object]]:
    return {item["name"]: item for item in document[kind]}  # type: ignore[index]


def _document_text(output: Path) -> str:
    """The document as written, with the run's own output path elided.

    Parsing it first would let a different key order or a different text form for
    the same value pass; the document is a committed artifact, so its bytes are
    what a rebuild has to reproduce.
    """
    text = (output / "meta_graph.json").read_text(encoding="utf-8")
    return text.replace(json.dumps(str(output))[1:-1], "<output>")


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

    def test_graph_properties_are_scalar_or_flat_scalar_arrays(self) -> None:
        with self.assertRaisesRegex(TypeError, "must be a scalar"):
            class StructuredNode(Node):
                location: PropertySlot[Place | None] = property()  # type: ignore[valid-type]

        with self.assertRaisesRegex(TypeError, "require scalar items"):
            class NestedArrayNode(Node):
                codes: PropertySlot[Array[Array[str]]] = property()  # type: ignore[valid-type]

        with self.assertRaisesRegex(TypeError, "require non-null items"):
            class NullableItemNode(Node):
                codes: PropertySlot[Array[str | None]] = property()  # type: ignore[valid-type]

        class ScalarArrayNode(Node):
            codes: PropertySlot[Array[str]] = property()

        declaration = ScalarArrayNode._properties["codes"]
        self.assertEqual(declaration.logical_type, ArrayType(UnitType("str")))

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
             for unit in (bool, int, float, str, Date, Time, Timestamp, Uuid)],
            ["bool", "int", "float", "str", "date", "time", "timestamp", "uuid"],
        )
        self.assertEqual(
            [display_type(type_to_ir(normalize_type(unit | None)))
             for unit in (str, Timestamp, Uuid)],
            ["str | None", "timestamp | None", "uuid | None"],
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

    def test_the_full_operator_pipeline_reaches_every_consumer(self) -> None:
        """Validation and deduplication sit ahead of the graph-record consumers.

        The validator re-publishes the records it vetted and the deduplication
        collapses them further; a consumer wired to any earlier producer of the
        same role would see raw duplicates (the regression this pins), because
        role candidates are shared artifacts, not one-per-consumer tokens.
        """
        _output, contract, _report, document = _run(
            self,
            register_module(
                RejectConflictingNonNullValuesModule,
                RejectConflictingNonNullValuesConfiguration(fail_on_error=False),
            ),
            register_module(CollapseExactDuplicatesModule),
            register_module(MetaGraphModule),
        )
        nodes = _by_name(document, "nodes")
        self.assertEqual(nodes["person"]["counts"]["records"], 2)
        self.assertEqual(nodes["team"]["counts"]["records"], 2)
        producers = {
            connection.output_slot_id
            for connection in contract.workflow.connections
            if connection.input_slot_id == "meta_graph::document.records"
        }
        self.assertTrue(producers, "the document reads the graph artifacts")
        self.assertFalse(
            any(source.startswith("core::aggregate") for source in producers),
            f"raw aggregates leaked into the document: {sorted(producers)}",
        )
        # The export target gets the same treatment (over the sub-graph whose
        # endpoints are all bound, which is what the target requires).
        export_contract = compile(
            bindings=(ALL_BINDINGS[0], ALL_BINDINGS[1], ALL_BINDINGS[2]),
            sources=(_source(Path("unused.json")),),  # compiled, never built
            modules=(
                register_module(
                    RejectConflictingNonNullValuesModule,
                    RejectConflictingNonNullValuesConfiguration(fail_on_error=False),
                ),
                register_module(CollapseExactDuplicatesModule),
                register_module(Neo4jModule),
            ),
        )
        export_sources = {
            connection.output_slot_id
            for connection in export_contract.workflow.connections
            if connection.input_slot_id.startswith("neo4j::export.node.")
        }
        self.assertTrue(export_sources)
        self.assertFalse(
            any(source.startswith("core::aggregate") for source in export_sources),
            f"raw aggregates leaked into the export: {sorted(export_sources)}",
        )

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
            # Both output paths name a temporary directory that differs between
            # runs; everything else must match byte for byte.
            summary = dict(document["summary"])
            summary.pop("location")
            summary.pop("html_location", None)
            return json.dumps({**document, "summary": summary}, sort_keys=True)

        self.assertEqual(body(first), body(second))

    def test_written_document_bytes_are_identical_across_two_compilations(self) -> None:
        def written() -> str:
            output, _contract, _report, _document = _run(
                self, register_module(MetaGraphModule),
            )
            return _document_text(output)

        self.assertEqual(written(), written())

    def test_the_document_version_is_three(self) -> None:
        self.assertEqual(
            MetaGraphDocumentIR(relative_path="meta_graph.json").schema_version, 3,
        )
        _output, _contract, _report, document = _run(self, register_module(MetaGraphModule))
        self.assertEqual(document["schema_version"], 3)
        # A document written before the canonical temporal types arrived cannot be
        # read as this one: its example values are whatever str() made of them.
        stale = {
            "schema_version": 2, "relative_path": "meta_graph.json",
            "example_limit": 3, "include_html": True,
            "html_relative_path": "meta_graph.html", "components": [],
        }
        with self.assertRaises(ValueError):
            decode_meta_graph_instruction(stale)

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


class ExampleValueTests(unittest.TestCase):
    def test_properties_carry_values_from_the_emitted_records(self) -> None:
        _output, _contract, _report, document = _run(self, register_module(MetaGraphModule))
        person = _by_name(document, "nodes")["person"]
        name = next(item for item in person["properties"] if item["name"] == "name")
        self.assertEqual(set(name["examples"]), {"Ada", "Grace"})

    def test_examples_never_include_nulls(self) -> None:
        _output, _contract, _report, document = _run(self, register_module(MetaGraphModule))
        person = _by_name(document, "nodes")["person"]
        summary = next(
            item for item in person["properties"] if item["name"] == "summary"
        )
        self.assertNotIn(None, summary["examples"])
        self.assertEqual(summary["examples"], ["documented"])

    def test_example_limit_caps_values_per_property(self) -> None:
        _output, _contract, _report, document = _run(
            self,
            register_module(MetaGraphModule, MetaGraphModuleConfiguration(example_limit=1)),
        )
        for entry in document["nodes"] + document["edges"]:
            for prop in entry["properties"]:
                self.assertLessEqual(len(prop["examples"]), 1, entry["name"])

    def test_zero_example_limit_omits_examples_entirely(self) -> None:
        _output, _contract, _report, document = _run(
            self,
            register_module(MetaGraphModule, MetaGraphModuleConfiguration(example_limit=0)),
        )
        for entry in document["nodes"] + document["edges"]:
            for prop in entry["properties"]:
                self.assertNotIn("examples", prop)

    def test_an_abstract_component_inherits_examples_from_its_descendants(self) -> None:
        _output, _contract, _report, document = _run(self, register_module(MetaGraphModule))
        category = _by_name(document, "nodes")["documented"]
        self.assertEqual(category["counts"]["records"], 0)
        summary = next(
            item for item in category["properties"] if item["name"] == "summary"
        )
        self.assertEqual(summary["examples"], ["documented"])

    def test_examples_are_deterministic_across_builds(self) -> None:
        def collected() -> list[tuple[str, str, list[str]]]:
            _output, _contract, _report, document = _run(
                self, register_module(MetaGraphModule),
            )
            return [
                (entry["name"], prop["name"], sorted(str(v) for v in prop["examples"]))
                for entry in document["nodes"] + document["edges"]
                for prop in entry["properties"]
            ]

        self.assertEqual(collected(), collected())

    def test_the_example_method_is_recorded_in_the_document(self) -> None:
        _output, _contract, _report, document = _run(
            self,
            register_module(
                MetaGraphModule, MetaGraphModuleConfiguration(example_limit=2),
            ),
        )
        self.assertEqual(
            document["examples"], {"method": "approx_top_k", "limit": 2},
        )

    def test_example_limit_configuration_is_validated(self) -> None:
        with self.assertRaisesRegex(ValueError, "example limit"):
            MetaGraphModuleConfiguration(example_limit=-1)


class TemporalNode(Node):
    """One property per canonical type the document has to give a text form."""

    options = NodeOptions(name="temporal")

    occurred_at: PropertySlot[Timestamp] = property()
    recorded_at: PropertySlot[Timestamp | None] = property()
    on_day: PropertySlot[Date] = property()
    at_hour: PropertySlot[Time] = property()
    token: PropertySlot[Uuid] = property()


TEMPORAL_TEXT = {
    "occurred_at": "2026-08-02T14:20:00",
    "recorded_at": "2026-07-14T09:35:00",
    "on_day": "2026-08-02",
    "at_hour": "14:20:00",
    "token": "9b8e4c2e-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
}

# The nullable slot takes a non-null literal, so the document carries both the
# ``| None`` modifier and an example value for it.
temporal_binding = node_binding(
    target=TemporalNode,
    build_key=MetaInput.identifier,
    properties=TemporalNode(
        occurred_at=value_expression(datetime(2026, 8, 2, 14, 20)),
        recorded_at=value_expression(datetime(2026, 7, 14, 9, 35)),
        on_day=value_expression(date(2026, 8, 2)),
        at_hour=value_expression(time(14, 20)),
        token=value_expression(UUID(TEMPORAL_TEXT["token"])),
    ),
)


def _temporal_document(
    case: unittest.TestCase,
) -> tuple[Path, dict[str, object]]:
    output, _contract, _report, document = _run(
        case, register_module(MetaGraphModule), bindings=(temporal_binding,),
    )
    return output, document


class CanonicalTemporalPropertyTests(unittest.TestCase):
    """A temporal property's name, family and example spelling, end to end."""

    def setUp(self) -> None:
        self.output, self.document = _temporal_document(self)
        entry = _by_name(self.document, "nodes")["temporal"]
        self.properties = {item["name"]: item for item in entry["properties"]}

    def test_temporal_properties_are_named_in_the_canonical_vocabulary(self) -> None:
        self.assertEqual(
            [(item["name"], item["type"], item["nullable"])
             for item in self.properties.values()],
            [("occurred_at", "timestamp", False),
             ("recorded_at", "timestamp | None", True),
             ("on_day", "date", False), ("at_hour", "time", False),
             ("token", "uuid", False)],
        )

    def test_examples_are_written_in_the_canonical_text_form(self) -> None:
        # Read the file rather than the parsed document: the point of the
        # assertion is the spelling on disk, which `default=str` got wrong.
        written = (self.output / "meta_graph.json").read_text(encoding="utf-8")
        for name, text in TEMPORAL_TEXT.items():
            with self.subTest(name=name):
                self.assertEqual(self.properties[name]["examples"], [text])
                self.assertIn(f'"{text}"', written)
        self.assertNotIn("2026-08-02 14:20:00", written, "a space is not ISO-8601")

    def test_temporal_examples_are_written_identically_across_two_builds(self) -> None:
        # The sketch returns an order of its own, so a temporal example is only
        # reproducible because both the text and the order are defined here.
        def written() -> str:
            output, _document = _temporal_document(self)
            return _document_text(output)

        self.assertEqual(written(), written())

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_the_family_of_a_temporal_type_is_its_canonical_name(self) -> None:
        app = _APP_BLOCK.search(_html_text(self.output))
        assert app
        derived = _run_app_code(
            app.group(1),
            "console.log(JSON.stringify(Object.fromEntries("
            "  ['timestamp','timestamp | None','date','time','uuid']"
            "  .map(function (type) { return [type, typeFamily(type)]; }))));",
        )
        self.assertEqual(
            derived,
            {"timestamp": "timestamp", "timestamp | None": "timestamp",
             "date": "date", "time": "time", "uuid": "uuid"},
        )


class CanonicalExampleValueTests(unittest.TestCase):
    """The one text form and order an example value is written with."""

    def test_each_canonical_type_takes_its_documented_text_form(self) -> None:
        self.assertEqual(
            _canonical_example_value(datetime(2026, 8, 2, 14, 20)),
            "2026-08-02T14:20:00",
        )
        self.assertEqual(_canonical_example_value(date(2026, 8, 2)), "2026-08-02")
        self.assertEqual(_canonical_example_value(time(14, 20)), "14:20:00")
        self.assertEqual(
            _canonical_example_value(UUID(TEMPORAL_TEXT["token"])),
            TEMPORAL_TEXT["token"],
        )

    def test_the_json_scalars_pass_straight_through(self) -> None:
        for value in (None, True, 3, 1.5, "Ada"):
            with self.subTest(value=value):
                self.assertIs(_canonical_example_value(value), value)

    def test_containers_recurse_to_their_items(self) -> None:
        self.assertEqual(
            _canonical_example_value(
                {"at": datetime(2026, 8, 2, 14, 20), "days": [date(2026, 8, 2)]},
            ),
            {"at": "2026-08-02T14:20:00", "days": ["2026-08-02"]},
        )

    def test_a_value_outside_the_canonical_vocabulary_raises_naming_its_type(self) -> None:
        # Fail closed: `default=str` would have written these into a document the
        # build claims to be able to reproduce.
        for value in (b"bytes", Decimal("1.5"), timedelta(days=1)):
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, type(value).__name__) as caught:
                    _canonical_example_value(value)
                self.assertIn("no canonical form", str(caught.exception))

    def test_examples_order_by_canonical_text_form(self) -> None:
        # Not by repr, which would put the datetime first and 14:20 before 09:35.
        # The order is the one the document prints.
        values = [time(14, 20), datetime(2026, 8, 2, 9, 0), time(9, 35)]
        self.assertEqual(
            [_canonical_example_value(item)
             for item in sorted(values, key=_example_order_key)],
            ["09:35:00", "14:20:00", "2026-08-02T09:00:00"],
        )

    def test_the_secondary_key_separates_values_of_the_same_text_form(self) -> None:
        # A date and a string spelling it identically are the same text, so the
        # tie is broken by repr — deterministically, never by input order.
        spelled = "2026-08-02"
        keys = [_example_order_key(item) for item in (date(2026, 8, 2), spelled)]
        self.assertEqual({item[0] for item in keys}, {json.dumps(spelled)})
        self.assertEqual(len(set(keys)), 2)


class NullableKeyTable(Table):
    maybe_id: Field[str | None] = field()
    detail: Field[str] = field()


class EmptySetNode(Node):
    options = NodeOptions(name="empty_set")

    detail: PropertySlot[str] = property()


empty_set_binding = node_binding(
    target=EmptySetNode,
    build_key=NullableKeyTable.maybe_id.where_present(),
    properties=EmptySetNode(detail=NullableKeyTable.detail),
)


class EmptyProducingComponentTests(unittest.TestCase):
    def test_a_component_that_emits_no_rows_is_still_described(self) -> None:
        # An empty aggregate gives the sampling query no row to carry the
        # window count out on, so the count needs its own path.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "input.json"
            data.write_text(json.dumps([
                {"maybe_id": None, "detail": "first"},
                {"maybe_id": None, "detail": "second"},
            ]), encoding="utf-8")
            output = root / "output"
            contract = compile(
                bindings=(empty_set_binding,),
                sources=(bind_source(
                    target=NullableKeyTable,
                    config=DataSourceConfig(str(data), format=InputFormat.JSON),
                ),),
                modules=(register_module(MetaGraphModule),),
            )
            report = build(contract, output_directory=output)

            self.assertTrue(report.succeeded)
            document = json.loads(
                (output / "meta_graph.json").read_text(encoding="utf-8")
            )
            entry = _by_name(document, "nodes")["empty_set"]
            self.assertEqual(entry["counts"]["records"], 0)
            self.assertEqual(entry["counts"]["inclusive_records"], 0)
            self.assertEqual(entry["properties"][0]["examples"], [])


class _ScriptCounter(HTMLParser):
    """Counts script blocks and confirms the embedded data block is present."""

    def __init__(self) -> None:
        super().__init__()
        self.scripts = 0
        self.data_block = False

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "script":
            self.scripts += 1
            if ("id", "meta-graph-data") in list(attrs):
                self.data_block = True


_DATA_BLOCK = re.compile(
    r'<script id="meta-graph-data" type="application/json">(.*?)</script>', re.DOTALL
)
_APP_BLOCK = re.compile(r"/\* APP-START \*/(.*?)/\* APP-END \*/", re.DOTALL)
_STYLE_BLOCK = re.compile(r"<style>(.*?)</style>", re.DOTALL)


def _html_text(output: Path) -> str:
    return (output / "meta_graph.html").read_text(encoding="utf-8")


def _embedded(html: str) -> dict:
    match = _DATA_BLOCK.search(html)
    assert match, "the meta graph data block is missing"
    return json.loads(match.group(1).replace("<\\/", "</"))


def _run_app_code(app_code: str, driver: str) -> dict:
    """Run the page's DOM-free derivation code under node and read its output."""
    handle, name = tempfile.mkstemp(suffix=".js")
    os.close(handle)  # Windows refuses to reuse a path with a live descriptor.
    Path(name).write_text(app_code + "\n" + driver + "\n", encoding="utf-8")
    try:
        result = subprocess.run(
            ["node", name], capture_output=True, text=True, check=True,
        )
    finally:
        Path(name).unlink(missing_ok=True)
    return json.loads(result.stdout)


class HtmlVisualizationTests(unittest.TestCase):
    def test_html_is_written_beside_the_document(self) -> None:
        output, _contract, report, document = _run(self, register_module(MetaGraphModule))
        self.assertTrue((output / "meta_graph.html").is_file())
        self.assertTrue((output / "meta_graph.json").is_file())
        published = report.published_artifacts[0].value
        self.assertEqual(published["html_location"], str(output / "meta_graph.html"))
        self.assertEqual(document["summary"]["html_location"], published["html_location"])

    def test_html_embeds_the_same_document_as_the_json_file(self) -> None:
        output, _contract, _report, document = _run(self, register_module(MetaGraphModule))
        embedded = _embedded(_html_text(output))
        embedded["summary"].pop("location")
        document["summary"].pop("location")
        self.assertEqual(embedded, document)

    def test_html_is_a_single_self_contained_file(self) -> None:
        output, _contract, _report, _document = _run(self, register_module(MetaGraphModule))
        html = _html_text(output)
        self.assertIn("https://d3js.org v7", html, "d3 should be inlined, not referenced")
        self.assertIn("forceSimulation", html)
        external = re.findall(r'(?:src|href)\s*=\s*["\']([^"\']+)', html)
        self.assertEqual([u for u in external if not u.startswith("#")], [])

    def test_arrowheads_do_not_scale_with_stroke_width(self) -> None:
        # The default markerUnits is strokeWidth, so thickening a selected link
        # would enlarge its arrowhead and slide it off the node boundary.
        output, _contract, _report, _document = _run(self, register_module(MetaGraphModule))
        html = _html_text(output)
        self.assertIn("markerUnits", html)
        self.assertIn("userSpaceOnUse", html)
        self.assertIn("arrow-selected", html, "the highlight needs its own marker")

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_property_markup_and_type_families_are_correct(self) -> None:
        output, _contract, _report, _document = _run(self, register_module(MetaGraphModule))
        app = _APP_BLOCK.search(_html_text(output))
        assert app
        component = {
            "name": "x", "kind": "node", "label": "X", "symbol_id": "s", "abstract": False,
            "counts": {"records": 1, "inclusive_records": 1, "bindings": 1},
            "properties": [
                {"name": "title", "type": "str",
                 "description": 'A <tag> & "quote"', "examples": ["a"]},
                {"name": "count", "type": "int", "description": None, "examples": []},
                {"name": "flag", "type": "bool | None", "description": "d",
                 "examples": [True, False]},
                {"name": "tags", "type": "Array[str | None] | None", "description": "d",
                 "examples": []},
                {"name": "where", "type": "Place | None", "description": "d", "examples": []},
                {"name": "occurred_at", "type": "timestamp | None", "description": "d",
                 "examples": ["2026-08-02T14:20:00"]},
                {"name": "token", "type": "uuid", "description": "d",
                 "examples": ["9b8e4c2e-1a2b-3c4d-5e6f-7a8b9c0d1e2f"]},
            ],
        }
        derived = _run_app_code(
            app.group(1),
            "console.log(JSON.stringify({"
            " families: ['str','int','float','bool','str | None',"
            "   'Array[str | None] | None','Place | None','Currency',"
            "   'date','time','timestamp','uuid','Decimal',"
            "   'date | None','timestamp | None','uuid | None'].map(typeFamily),"
            " nullable: ['str','str | None','Array[str | None] | None','Array[str]']"
            "   .map(isNullable),"
            f" html: propertyList({json.dumps(component)})"
            "}));",
        )

        self.assertEqual(
            derived["families"],
            ["string", "number", "number", "boolean", "string", "array",
             "composite", "composite",
             "date", "time", "timestamp", "uuid", "composite",
             "date", "timestamp", "uuid"],
        )
        self.assertEqual(derived["nullable"], [False, True, True, False])

        html = derived["html"]
        for family in ("string", "number", "boolean", "array", "composite",
                       "timestamp", "uuid"):
            self.assertIn(f'class="type {family}"', html)
        # Every family the derivation can name is styled, so a new canonical type
        # cannot arrive as an unlabelled grey badge.
        css = _STYLE_BLOCK.search(_html_text(output))
        assert css
        for family in ("date", "time", "timestamp", "uuid"):
            self.assertRegex(css.group(1), rf"\.type\.{family}\b")
        # Nullable is a badge, so four of the seven properties carry it.
        self.assertEqual(html.count('class="nullable"'), 4)
        self.assertIn("&lt;tag&gt; &amp; &quot;quote&quot;", html)
        self.assertNotIn("<tag>", html)
        self.assertIn("No description.", html, "a null description is still labelled")
        self.assertEqual(html.count("None observed."), 3)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_only_colliding_edges_are_asked_to_curve(self) -> None:
        output, _contract, _report, _document = _run(self, register_module(MetaGraphModule))
        app = _APP_BLOCK.search(_html_text(output))
        assert app
        derived = _run_app_code(
            app.group(1),
            "const links = ["
            " {source:'a', target:'b', component:{name:'e1'}},"
            " {source:'a', target:'b', component:{name:'e2'}},"
            " {source:'b', target:'a', component:{name:'e3'}},"
            " {source:'a', target:'c', component:{name:'e4'}},"
            " {source:'a', target:'a', component:{name:'self'}}];\n"
            "spreadLinks(links);\n"
            "console.log(JSON.stringify(links.map(function (l) {\n"
            "  return l.component.name + ':' + l.spread;\n"
            "})));",
        )
        # One edge per pair draws straight; three between a and b fan out
        # symmetrically; a self-declaration is handled by geometry, not spread.
        self.assertEqual(
            derived, ["e1:-1", "e2:0", "e3:1", "e4:0", "self:0"],
        )

    def test_interaction_surfaces_are_singular_and_inert_lines_are_marked(self) -> None:
        output, _contract, _report, _document = _run(self, register_module(MetaGraphModule))
        html = _html_text(output)
        # One feedback surface: the panel. No second tooltip widget, and no
        # per-shape <title> that would label a hierarchy line as a component.
        self.assertNotIn("hover-card", html)
        self.assertEqual(html.count("<title>"), 1, "only the document title")
        self.assertIn("canHover", html)          # hover is gated by the lock
        self.assertIn("renderPanel", html)
        # Hover and click share one view builder, so a hover highlights the same
        # relationships a click does.
        self.assertIn("focusOf", html)
        self.assertIn("[selected, hovered].filter(Boolean)", html)
        self.assertIn("arrow-associated", html)
        # Every link group carries its kind so a hierarchy line can be styled and
        # treated as non-interactive, and the arrow follows the line's emphasis.
        self.assertIn("'link-group ' + link.type", html)
        self.assertIn("arrow-hover", html)

    def test_edge_labels_are_styled_apart_from_node_labels(self) -> None:
        output, _contract, _report, _document = _run(self, register_module(MetaGraphModule))
        html = _html_text(output)
        self.assertIn("'link-label'", html)
        rule = html.split(".link-label {", 1)[1].split("}", 1)[0]
        self.assertIn("monospace", rule)
        self.assertIn("italic", rule)
        # An outer halo, painted under the fill so the glyphs stay crisp.
        for prop in ("paint-order: stroke", "stroke: var(--canvas)",
                     "stroke-width: 3px", "stroke-linejoin: round"):
            self.assertIn(prop, rule)
        self.assertIn("--canvas:", html)
        # Labels are hit-testable and bubble to their own group, so a name can be
        # pointed at as easily as the shape it labels.
        self.assertNotIn("pointer-events: none", rule)
        self.assertIn("cursor: pointer", rule)
        node_rule = html.split(".node text {", 1)[1].split("}", 1)[0]
        self.assertNotIn("italic", node_rule)
        self.assertNotIn("pointer-events: none", node_rule)
        self.assertIn("font-weight: 600", node_rule)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_self_loop_is_a_circular_arc_perpendicular_at_both_ends(self) -> None:
        output, _contract, _report, _document = _run(self, register_module(MetaGraphModule))
        app = _APP_BLOCK.search(_html_text(output))
        assert app
        # An arc's tangent is perpendicular to its own radius, so the tangent
        # meets the node square on exactly when that radius is perpendicular to
        # the node's radius at the anchor.
        derived = _run_app_code(app.group(1), r"""
const node = { x: 200, y: 150, radius: 18 };
const g = loopGeometry(node);
const d = selfLoop(node);
const cross = (u, v) => u.x * v.y - u.y * v.x;
const dot = (u, v) => u.x * v.x + u.y * v.y;
const TWO_PI = 2 * Math.PI;
const ang = (p) => (Math.atan2(p.y - g.cy, p.x - g.cx) + TWO_PI) % TWO_PI;
const a0 = ang({ x: g.ax, y: g.ay }), a1 = ang({ x: g.bx, y: g.by });
const sweep = (a1 - a0 + TWO_PI) % TWO_PI;
const top = (Math.atan2(g.top - g.cy, 1e-9) + TWO_PI) % TWO_PI;
const arc = d.match(/A([-\d.]+),([-\d.]+) 0 (\d) (\d)/);
console.log(JSON.stringify({
  stemIsRadial: Math.abs(cross({ x: g.ax - node.x, y: g.ay - node.y },
                               { x: g.sx - node.x, y: g.sy - node.y })) < 1e-9,
  leavesPerpendicular: Math.abs(dot({ x: g.ax - g.cx, y: g.ay - g.cy },
                                    { x: g.ax - node.x, y: g.ay - node.y })) < 1e-9,
  returnsPerpendicular: Math.abs(dot({ x: g.bx - g.cx, y: g.by - g.cy },
                                     { x: g.bx - node.x, y: g.by - node.y })) < 1e-9,
  singleCircle: !!arc && arc[1] === arc[2] && Math.abs(+arc[1] - g.radius) < 1e-9,
  // The run over the top spans 180 + 2*theta degrees, so it must be flagged as
  // the major arc travelling in the positive angle direction.
  majorArc: sweep > Math.PI,
  largeArcFlag: !!arc && arc[3] === '1',
  sweepFlag: !!arc && arc[4] === '1',
  passesOverTheTop: ((top - a0 + TWO_PI) % TWO_PI) <= sweep,
  tipReachesSurface: Math.abs(g.rho - node.radius - ARROW_LENGTH) < 1e-9,
}));
""")
        self.assertEqual(derived, {key: True for key in derived}, str(derived))

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_panel_attributes_inherited_properties_to_their_category(self) -> None:
        output, _contract, _report, _document = _run(self, register_module(MetaGraphModule))
        app = _APP_BLOCK.search(_html_text(output))
        assert app
        derived = _run_app_code(app.group(1), """
const ancestors = [{ name: 'documented', properties: [{ name: 'summary' }] }];
const component = {
  name: 'defect', kind: 'node', label: 'Defect', symbol_id: 's', abstract: false,
  counts: { records: 1, inclusive_records: 1, bindings: 1 },
  properties: [
    { name: 'summary', type: 'str', description: 'd', examples: ['x'] },
    { name: 'title', type: 'str', description: 'd', examples: ['y'] },
  ],
};
const html = propertyList(component, ancestors);
console.log(JSON.stringify({
  summaryOrigin: propertyOrigin('summary', ancestors),
  titleOrigin: propertyOrigin('title', ancestors),
  noAncestors: propertyOrigin('summary', []),
  badges: (html.match(/class="inherited"/g) || []).length,
  badgeText: (html.match(/class="inherited">([^<]+)</) || [])[1],
  heading: (html.match(/<h3>[^<]*(?:<[^>]+>[^<]*<\/span>)?[^<]*<\/h3>/) || [])[0],
}));
""")
        self.assertEqual(derived["summaryOrigin"], "documented")
        self.assertIsNone(derived["titleOrigin"], "own properties carry no attribution")
        self.assertIsNone(derived["noAncestors"])
        self.assertEqual(derived["badges"], 1, "only the inherited one is marked")
        self.assertEqual(derived["badgeText"], "from documented")
        self.assertIn("1 inherited", derived["heading"])

    def test_html_can_be_disabled(self) -> None:
        output, _contract, report, document = _run(
            self,
            register_module(MetaGraphModule, MetaGraphModuleConfiguration(include_html=False)),
        )
        self.assertFalse((output / "meta_graph.html").exists())
        self.assertTrue((output / "meta_graph.json").is_file())
        self.assertNotIn("html_location", document["summary"])
        self.assertNotIn("html_location", report.published_artifacts[0].value)

    def test_html_path_is_validated(self) -> None:
        with self.assertRaisesRegex(ValueError, "HTML path"):
            MetaGraphModuleConfiguration(html_relative_path="../escape.html")

    def test_a_closing_tag_in_the_data_cannot_break_the_block(self) -> None:
        payload = {"nodes": [], "edges": [], "summary": {},
                   "note": "</script><script>alert(1)</script>"}
        html = render(payload)
        self.assertEqual(html.count("</script>"), 3, "only the three real script blocks")
        self.assertIn("<\\/script>", html, "the payload should be escaped")
        self.assertEqual(_embedded(html)["note"], payload["note"])

    def test_html_parses_as_a_single_document(self) -> None:
        output, _contract, _report, _document = _run(self, register_module(MetaGraphModule))
        parser = _ScriptCounter()
        parser.feed(_html_text(output))
        self.assertEqual(parser.scripts, 3)
        self.assertTrue(parser.data_block)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_the_derivation_runs_outside_a_browser(self) -> None:
        output, _contract, _report, document = _run(self, register_module(MetaGraphModule))
        app = _APP_BLOCK.search(_html_text(output))
        assert app, "the app derivation block is missing"
        derived = _run_app_code(
            app.group(1),
            "const data = " + json.dumps(document) + ";\n"
            "const graph = buildGraph(data);\n"
            "const names = graph.nodes.map(function (n) { return n.name; });\n"
            "const unresolved = graph.links.filter(function (l) {\n"
            "  return names.indexOf(l.source) < 0 || names.indexOf(l.target) < 0;\n"
            "});\n"
            "const touched = new Set();\n"
            "graph.links.forEach(function (l) { touched.add(l.source); touched.add(l.target); });\n"
            "const index = new Map(data.nodes.concat(data.edges).map(function (c) { return [c.name, c]; }));\n"
            "const samples = [\n"
            "  data.nodes.filter(function (c) { return c.parent; })[0],\n"
            "  data.edges.filter(function (c) { return c.parent; })[0],\n"
            "  data.edges.filter(function (c) { return c.abstract; })[0],\n"
            "];\n"
            "console.log(JSON.stringify({\n"
            "  nodes: names,\n"
            "  ancestors: samples.map(function (c) {\n"
            "    return c.name + '=' + ancestorNames(index, c).join('+');\n"
            "  }),\n"
            "  relations: graph.links.filter(function (l) { return l.type === 'relation'; }).length,\n"
            "  hierarchy: graph.links.filter(function (l) { return l.type === 'hierarchy'; }).length,\n"
            "  categories: graph.links.filter(function (l) { return l.type === 'category'; })\n"
            "    .map(function (l) { return l.component.name + ':' + l.source + '->' + l.target; }),\n"
            "  unresolved: unresolved.length,\n"
            "  isolated: names.filter(function (n) { return !touched.has(n); }),\n"
            "}));",
        )

        concrete = [e for e in document["edges"] if not e["abstract"]]
        # The abstraction chain must be the same one the page draws with.
        node_sample = next(n for n in document["nodes"] if n["parent"])
        edge_sample = next(e for e in document["edges"] if e["parent"])
        abstract_sample = next(e for e in document["edges"] if e["abstract"])
        self.assertEqual(
            derived["ancestors"],
            [
                f"{node_sample['name']}={node_sample['parent']}",
                f"{edge_sample['name']}={edge_sample['parent']}",
                f"{abstract_sample['name']}={abstract_sample['parent'] or ''}",
            ],
        )
        abstract_edges = [e["name"] for e in document["edges"] if e["abstract"]]
        categories = {n["name"] for n in document["nodes"]}
        self.assertEqual(derived["unresolved"], 0)
        self.assertEqual(derived["relations"], len(concrete))
        for name in categories:
            self.assertIn(name, derived["nodes"])
        # An abstract edge is a declaration over endpoint kinds, so it draws as a
        # link between those kinds rather than being dropped or floated as a node.
        self.assertEqual(
            derived["categories"],
            [f"{name}:documented->documented" for name in abstract_edges],
        )
        for name in abstract_edges:
            self.assertNotIn(name, derived["nodes"])
        self.assertEqual(derived["isolated"], [], "every vertex must be connected")


class ArrayExampleTable(Table):
    identifier: Field[str] = field()
    codes: Field[Array[str | None]] = field()


class ArrayExampleNode(Node):
    codes: PropertySlot[Array[str]] = property()


array_example_binding = node_binding(
    target=ArrayExampleNode,
    build_key=ArrayExampleTable.identifier,
    properties=ArrayExampleNode(codes=ArrayExampleTable.codes.without_nulls()),
)


class ArrayExampleTests(unittest.TestCase):
    """Array-valued properties carry examples: list values are unhashable."""

    def test_array_property_examples_survive_deduplication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "input.json"
            data.write_text(json.dumps([
                {"identifier": "a", "codes": ["x", "y"]},
                {"identifier": "b", "codes": ["x", "y"]},
                {"identifier": "c", "codes": ["z"]},
            ]), encoding="utf-8")
            output = root / "output"
            contract = compile(
                bindings=(array_example_binding,),
                sources=(bind_source(
                    target=ArrayExampleTable,
                    config=DataSourceConfig(str(data), format=InputFormat.JSON),
                ),),
                modules=(register_module(MetaGraphModule),),
            )
            report = build(contract, output_directory=output)
            self.assertTrue(report.succeeded)
            document = json.loads(
                (output / "meta_graph.json").read_text(encoding="utf-8")
            )
            entry = next(
                item for item in document["nodes"]
                if item["counts"]["records"] == 3
            )
            self.assertEqual(entry["properties"][0]["examples"], [["x", "y"], ["z"]])


if __name__ == "__main__":
    unittest.main()
