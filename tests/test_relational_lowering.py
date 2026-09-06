from __future__ import annotations

import datetime
import json
import tempfile
import unittest
import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from kg_build_system import (
    Array, BuildRuntime, DataSourceConfig, Field, InputFormat, Node, Projection,
    PropertySlot, Struct, Table, bind_source, build, compile, create_blueprint,
    field, node_binding, projection_field, property,
)
from kg_build_system._frozen_json import freeze_json
from kg_build_system.modules import (
    CollapseExactDuplicatesModule, FileModule, FileModuleConfiguration,
    MergeCompatibleFactsModule, MergeCompatibleFactsModuleConfiguration,
    register_module,
)
from kg_build_system.modules.core import graph_record_components
from kg_build_system.modules.core.credentials import configure_source_credentials
from kg_build_system.modules.core.core import CoreArtifactRoles
from kg_build_system.modules.targets.file import FileExecutor
from kg_build_system.relational import lower_product
from kg_build_system.engines.duckdb import lower_relation_sql
from kg_build_system.workflow.ir import WorkflowContractIR
from kg_build_system.workflow.models import (
    Artifact, ContinuableInput, ExecutionContext, ModuleDefinition, ModuleReference,
    OutputSlot, StepStatus, WorkflowArtifactRoles, WorkflowStep,
)
from kg_build_system.workflow.services import RelationRef


class LoweringEvidence(Struct):
    labels: Field[Array[str]] = field()


class LoweringInput(Table):
    identifier: Field[str] = field()
    optional_label: Field[str | None] = field()
    evidence: Field[Array[LoweringEvidence]] = field()


class LoweringProjection(Projection):
    identifier = projection_field(LoweringInput.identifier)
    label = projection_field(
        LoweringInput.evidence.expand()
        .pick(lambda item: item.labels)
        .expand()
        .expression.append("!")
    )


class LoweringNode(Node):
    label: PropertySlot[str] = property()


class Keyword(Struct):
    keyword_id: Field[str] = field()
    keyword_type: Field[str] = field()


class NullableKeyword(Struct):
    keyword_id: Field[str] = field()
    note: Field[str | None] = field()


class KeywordInput(Table):
    identifier: Field[str] = field()
    keyword_type: Field[str] = field()
    keywords: Field[Array[Keyword]] = field()
    optional_keywords: Field[Array[Keyword] | None] = field()


class NullableKeywordInput(Table):
    identifier: Field[str] = field()
    keywords: Field[Array[NullableKeyword]] = field()


class KeywordNode(Node):
    label: PropertySlot[str] = property()


class KeywordCollectionNode(Node):
    ids: PropertySlot[Array[str]] = property()
    optional_ids: PropertySlot[Array[str] | None] = property()


class NullableMemberNode(Node):
    notes: PropertySlot[Array[str]] = property()


class RelationalLoweringTests(unittest.TestCase):
    def test_nested_expansions_are_parent_first_and_shared(self) -> None:
        first = (
            LoweringInput.evidence.expand()
            .pick(lambda item: item.labels)
            .expand()
            .expression.append("!")
        )
        plan = lower_product(
            {
                "first": first.model,
                "second": first.model,
                "present": LoweringInput.optional_label.where_present().expression.model,
            },
            {"lowering_input": "input_relation"},
        )
        self.assertEqual(
            tuple(expansion.scope for expansion in plan.expands),
            (
                ("lowering_input", "evidence"),
                ("lowering_input", "evidence", "labels"),
            ),
        )
        sql = lower_relation_sql(plan)
        self.assertEqual(sql.count("UNNEST"), 2)
        self.assertIn("IS NULL", sql)
        self.assertIn("WHERE NOT", sql)
        self.assertIn("CONCAT", sql.upper())

    def test_compilation_preserves_the_blueprint_in_contract_json(self) -> None:
        source = bind_source(
            target=LoweringInput,
            config=DataSourceConfig("input.json", format=InputFormat.JSON),
        )
        binding = node_binding(
            target=LoweringNode,
            build_key=LoweringProjection.identifier,
            properties=LoweringNode(label=LoweringProjection.label),
        )
        blueprint = create_blueprint(
            bindings=(binding,), sources=(source,),
            modules=(register_module(
                FileModule, FileModuleConfiguration("graph.jsonl")
            ),),
        )
        self.assertEqual(
            tuple(module.module_id for module in blueprint.modules),
            (FileModule.ID, "core"),
        )
        contract = compile(
            blueprint=blueprint,
            modules=(register_module(
                FileModule, FileModuleConfiguration("graph.jsonl")
            ),),
        )
        restored = WorkflowContractIR.model_validate_json(
            contract.model_dump_json()
        )
        self.assertEqual(restored.workflow, contract.workflow)
        contract_document = json.loads(contract.model_dump_json())
        self.assertEqual(contract_document["schema_version"], 1)
        self.assertEqual(
            contract_document["provenance"]["compile"]["blueprint"]["schema_version"],
            blueprint.schema_version,
        )
        self.assertNotIn("blueprint", contract_document)
        self.assertTrue(all(
            "priority" not in module["reference"]
            for module in contract_document["workflow"]["modules"]
        ))
        self.assertTrue(all(
            "assembly_preference" not in step
            for step in contract_document["workflow"]["steps"]
        ))
        projection_step = next(
            step for step in contract.workflow.steps
            if step.step_id == f"core::projection.{blueprint.projections[0].name}"
        )
        self.assertEqual(str(projection_step.payload["sql"]).count("UNNEST"), 2)  # type: ignore[index]

    def test_source_instruction_retains_credential_reference(self) -> None:
        source = bind_source(
            target=LoweringInput,
            config=DataSourceConfig(
                "s3://bucket/input.json",
                format=InputFormat.JSON,
                credentials="source_credentials",
            ),
        )
        binding = node_binding(
            target=LoweringNode,
            build_key=LoweringProjection.identifier,
            properties=LoweringNode(label=LoweringProjection.label),
        )
        contract = compile(
            bindings=(binding,), sources=(source,), modules=(),
        )
        source_step = next(
            step for step in contract.workflow.steps
            if step.step_id == "core::table.lowering_input"
        )
        # The source step carries what the contract knows about the contract, so
        # the shape check and the null-count pre-flight can run without a
        # blueprint. Only paths the build reads that claim non-nullity are listed:
        # a read of an expanded array reaches the members below it, and a Parquet
        # path carries one pair of list wrappers per array level crossed.
        self.assertEqual(source_step.payload, {
            "action": "source_relation",
            "relation": "kg_table_0",
            "location": "s3://bucket/input.json",
            "format": "json",
            "credential_reference": "source_credentials",
            "declaration": "lowering_input",
            "declared_columns": [
                {"name": "identifier", "logical_type": {"kind": "unit", "name": "str"}},
                {"name": "optional_label", "logical_type": {
                    "kind": "nullable", "value": {"kind": "unit", "name": "str"}}},
                {"name": "evidence", "logical_type": {
                    "kind": "array", "item": {
                        "kind": "struct", "module": "test_relational_lowering",
                        "qualname": "LoweringEvidence"}}},
            ],
            "declared_paths": [
                {"logical_path": "evidence", "schema_path": "evidence.list.element"},
                {
                    "logical_path": "evidence.labels",
                    "schema_path": "evidence.list.element.labels.list.element",
                },
                {"logical_path": "identifier", "schema_path": "identifier"},
            ],
        })

    def test_core_module_owns_source_credential_options(self) -> None:
        services = MagicMock()
        services.credentials.resolve.return_value = json.dumps({
            "filesystem_options": {
                "key": "runtime-key",
                "secret": "runtime-secret",
            },
        })
        filesystem = object()
        with patch("fsspec.filesystem", return_value=filesystem) as factory:
            configure_source_credentials(
                services,
                location="s3://bucket/input.json",
                credential_reference="source_credentials",
            )

        services.credentials.resolve.assert_called_once_with("source_credentials")
        factory.assert_called_once_with(
            "s3", key="runtime-key", secret="runtime-secret",
        )
        services.relations.register_filesystem.assert_called_once_with(filesystem)

    def test_compiled_workflow_executes_and_publishes_file_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "input.json"
            source_path.write_text(json.dumps([{
                "identifier": "entity-1",
                "optional_label": None,
                "evidence": [{"labels": ["one", "two"]}],
            }]), encoding="utf-8")
            source = bind_source(
                target=LoweringInput,
                config=DataSourceConfig(str(source_path), format=InputFormat.JSON),
            )
            binding = node_binding(
                target=LoweringNode,
                build_key=LoweringProjection.identifier,
                properties=LoweringNode(label=LoweringProjection.label),
            )
            contract = compile(
                bindings=(binding,), sources=(source,),
                modules=(
                    register_module(
                        FileModule, FileModuleConfiguration("graph.jsonl")
                    ),
                    register_module(CollapseExactDuplicatesModule),
                ),
            )
            report = build(
                contract,
                BuildRuntime(duckdb_storage="disk"),
                output_directory=root / "output",
                working_directory=root / "working",
            )
            self.assertTrue(report.succeeded)
            rows = [
                json.loads(line)
                for line in (root / "output" / "graph.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(sorted(row["label"] for row in rows), ["one!", "two!"])
            self.assertEqual(len(report.published_artifacts), 1)
            self.assertEqual(
                tuple((root / "working").glob(".kg-build-duckdb-*")), ()
            )

    def test_global_assembly_connects_a_target_to_the_terminal_graph_records(self) -> None:
        source = bind_source(
            target=LoweringInput,
            config=DataSourceConfig("input.json", format=InputFormat.JSON),
        )
        binding = node_binding(
            target=LoweringNode,
            build_key=LoweringProjection.identifier,
            properties=LoweringNode(label=LoweringProjection.label),
        )
        blueprint = create_blueprint(
            bindings=(binding,),
            sources=(source,),
            modules=(
                register_module(
                    FileModule, FileModuleConfiguration("graph.jsonl")
                ),
                register_module(MergeCompatibleFactsModule),
                register_module(CollapseExactDuplicatesModule),
            ),
        )
        contract = compile(
            blueprint=blueprint,
            modules=(
                register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
                register_module(CollapseExactDuplicatesModule),
            ),
        )
        file_outputs = {
            connection.output_slot_id
            for connection in contract.workflow.connections
            if connection.input_slot_id == "file::write.records"
        }
        self.assertEqual(len(file_outputs), 1)
        self.assertTrue(
            next(iter(file_outputs)).startswith("collapse_exact_duplicates::")
        )

    def test_merge_scoping_emits_steps_only_for_named_components(self) -> None:
        class ScopedNode(Node):
            key: PropertySlot[str] = property()

        class OtherInput(Table):
            identifier: Field[str] = field()

        source = bind_source(
            target=LoweringInput,
            config=DataSourceConfig("input.json", format=InputFormat.JSON),
        )
        other_source = bind_source(
            target=OtherInput,
            config=DataSourceConfig("other.json", format=InputFormat.JSON),
        )
        binding = node_binding(
            target=LoweringNode,
            build_key=LoweringProjection.identifier,
            properties=LoweringNode(label=LoweringProjection.label),
        )
        other_binding = node_binding(
            target=ScopedNode,
            build_key=OtherInput.identifier,
            properties=ScopedNode(key=OtherInput.identifier),
        )
        blueprint = create_blueprint(
            bindings=(binding, other_binding),
            sources=(source, other_source),
            modules=(register_module(MergeCompatibleFactsModule),),
        )
        scoped_name = next(
            component.name
            for component in graph_record_components(blueprint)
            if "wering" in component.name
        )
        contract = compile(
            bindings=(binding, other_binding),
            sources=(source, other_source),
            modules=(
                register_module(
                    MergeCompatibleFactsModule,
                    MergeCompatibleFactsModuleConfiguration(
                        components=(scoped_name,)
                    ),
                ),
                register_module(CollapseExactDuplicatesModule),
                register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
            ),
        )
        merge_steps = [
            step.step_id
            for step in contract.workflow.steps
            if step.module_id == "merge_compatible_facts"
        ]
        self.assertEqual(merge_steps, [f"merge_compatible_facts::{scoped_name}"])
        with self.assertRaises(TypeError):
            MergeCompatibleFactsModuleConfiguration(components=("ok", ""))


class _RecordQuery:
    """The cursor result of ``SELECT * FROM <records>``, rows as DuckDB returns them."""

    def __init__(
        self, columns: tuple[str, ...], rows: list[tuple[object, ...]],
    ) -> None:
        self.description = tuple((column,) for column in columns)
        self._rows = rows

    def fetchmany(self, size: int) -> list[tuple[object, ...]]:
        batch, self._rows = self._rows[:size], self._rows[size:]
        return batch


class FileTargetPropertyEncodingTests(unittest.TestCase):
    """The file target writes the canonical text form of every property value."""

    def _write(
        self, root: Path, columns: tuple[str, ...], *rows: tuple[object, ...],
    ) -> str:
        services = MagicMock()
        services.output_storage.child.side_effect = lambda relative: root / relative
        services.relations.reference.return_value = "kg_records"
        services.relations.query.return_value = _RecordQuery(columns, list(rows))
        records = Artifact(
            "core::graph.node.survey",
            CoreArtifactRoles.graph_records("node", "survey"),
            RelationRef("kg_records"),
        )

        FileExecutor({}).handle(ExecutionContext(
            module=ModuleDefinition(ModuleReference(
                module_id=FileModule.ID,
                import_module=FileModule.__module__,
                class_qualname=FileModule.__qualname__,
                implementation_version=FileModule.VERSION,
                configuration=freeze_json({"relative_path": "graph.jsonl"}),
            )),
            step=WorkflowStep(
                step_id="file::write",
                module_id=FileModule.ID,
                outputs=(OutputSlot(
                    "file::write.result",
                    WorkflowArtifactRoles.published(FileModule.ID, "write_result"),
                ),),
            ),
            runtime_configuration={},
            inputs={"file::write.records": (ContinuableInput(
                output_slot_id=records.slot_id,
                status=StepStatus.SUCCEEDED,
                artifact=records,
            ),)},
            services=services,
        ))
        return (root / "graph.jsonl").read_text(encoding="utf-8")

    def test_scalars_are_written_exactly_as_before(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            written = self._write(
                Path(directory),
                ("build_key", "count", "ratio", "flag", "label", "note"),
                ("survey::1", 3, 1.5, True, "x", None),
            )
        self.assertEqual(
            written,
            '{"build_key": "survey::1", "count": 3, "flag": true, "kind": "node",'
            ' "label": "x", "note": null, "ratio": 1.5, "type": "survey"}\n',
        )

    def test_temporal_and_identifier_values_use_their_canonical_form(self) -> None:
        identifier = uuid.UUID("2f9c1b6a-5d4e-4a3b-8c7d-6e5f4a3b2c1d")
        with tempfile.TemporaryDirectory() as directory:
            written = self._write(
                Path(directory),
                ("build_key", "on_day", "at", "clock", "id", "stays", "window"),
                (
                    "survey::1",
                    datetime.date(2026, 8, 2),
                    datetime.datetime(2026, 7, 14, 6, 15),
                    datetime.time(6, 15),
                    identifier,
                    [datetime.date(2026, 8, 2), datetime.time(6, 15)],
                    {"start": datetime.datetime(2026, 7, 14, 6, 15), "codes": (identifier,)},
                ),
            )
        self.assertEqual(json.loads(written), {
            "build_key": "survey::1",
            "on_day": "2026-08-02",
            "at": "2026-07-14T06:15:00",
            "clock": "06:15:00",
            "id": "2f9c1b6a-5d4e-4a3b-8c7d-6e5f4a3b2c1d",
            "stays": ["2026-08-02", "06:15:00"],
            "window": {
                "start": "2026-07-14T06:15:00",
                "codes": ["2f9c1b6a-5d4e-4a3b-8c7d-6e5f4a3b2c1d"],
            },
            "kind": "node",
            "type": "survey",
        })
        # The str() form of a datetime separates the date from the time with a
        # space, which is not the ISO-8601 canonical text form.
        self.assertIn('"at": "2026-07-14T06:15:00"', written)
        self.assertNotIn("2026-07-14 06:15:00", written)

    def test_a_temporal_build_key_takes_its_canonical_text_form(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            written = self._write(
                Path(directory),
                ("build_key", "recorded"),
                ("survey::1", "kept"),
                (datetime.datetime(2026, 7, 14, 6, 15), "written"),
            )
        # The str build key is written with the bytes it always had; the
        # datetime key is text in canonical form, not str()'s space separator.
        self.assertEqual(
            written,
            '{"build_key": "survey::1", "kind": "node", "recorded": "kept",'
            ' "type": "survey"}\n'
            '{"build_key": "2026-07-14T06:15:00", "kind": "node",'
            ' "recorded": "written", "type": "survey"}\n',
        )

    def test_a_value_without_a_canonical_form_aborts_the_write(self) -> None:
        for refused in (b"blob", Decimal("1.5"), datetime.timedelta(days=1)):
            with self.subTest(refused=refused), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with self.assertRaises(TypeError) as failure:
                    self._write(root, ("build_key", "value"), ("survey::1", refused))
                self.assertIn(type(refused).__name__, str(failure.exception))
                self.assertEqual(
                    (root / "graph.jsonl").read_text(encoding="utf-8"), "",
                    "the record is refused rather than stringified",
                )


class ArrayPropertyTests(unittest.TestCase):
    """A flat, non-null scalar array is a first-class graph property."""

    def test_without_nulls_builds_a_neo4j_and_json_array_property(self) -> None:
        class TaggedNode(Node):
            codes: PropertySlot[Array[str]] = property()
            optional_codes: PropertySlot[Array[str] | None] = property()

        class Tagged(Table):
            identifier: Field[str] = field()
            codes: Field[Array[str | None]] = field()
            optional_codes: Field[Array[str | None] | None] = field()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "tagged.json"
            source_path.write_text(json.dumps([
                {"identifier": "a", "codes": ["x", None, "y"],
                 "optional_codes": None},
                {"identifier": "b", "codes": ["z"], "optional_codes": ["p", None]},
            ]), encoding="utf-8")
            source = bind_source(
                target=Tagged,
                config=DataSourceConfig(str(source_path), format=InputFormat.JSON),
            )
            binding = node_binding(
                target=TaggedNode,
                build_key=Tagged.identifier,
                properties=TaggedNode(
                    codes=Tagged.codes.without_nulls(),
                    optional_codes=Tagged.optional_codes.without_nulls(),
                ),
            )
            contract = compile(
                bindings=(binding,), sources=(source,),
                modules=(register_module(FileModule, FileModuleConfiguration("graph.jsonl")),),
            )
            report = build(contract, output_directory=root / "output")
            self.assertTrue(report.succeeded)
            rows = {
                row["build_key"]: row
                for row in (
                    json.loads(line)
                    for line in (root / "output" / "graph.jsonl")
                    .read_text(encoding="utf-8").splitlines()
                )
            }
            self.assertEqual(rows["a"]["codes"], ["x", "y"])
            self.assertIsNone(rows["a"]["optional_codes"])
            self.assertEqual(rows["b"]["codes"], ["z"])
            self.assertEqual(rows["b"]["optional_codes"], ["p"])

    def test_sorted_join_serialize_an_array_into_scalar_key_material(self) -> None:
        class TaggedNode(Node):
            identifier: PropertySlot[str] = property()
            tag_text: PropertySlot[str | None] = property()

        class Tagged(Table):
            identifier: Field[str] = field()
            tags: Field[Array[str]] = field()
            optional_tags: Field[Array[str] | None] = field()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "tagged.json"
            source_path.write_text(json.dumps([
                {"identifier": "a", "tags": ["y", "x"], "optional_tags": ["c", "a", "b"]},
                {"identifier": "b", "tags": ["only"], "optional_tags": None},
            ]), encoding="utf-8")
            source = bind_source(
                target=Tagged,
                config=DataSourceConfig(str(source_path), format=InputFormat.JSON),
            )
            binding = node_binding(
                target=TaggedNode,
                build_key=(
                    Tagged.identifier.expression.prepend("tagged::")
                    .append("#").append(Tagged.tags.sorted().join(",").expression)
                ),
                properties=TaggedNode(
                    identifier=Tagged.identifier,
                    tag_text=Tagged.optional_tags.sorted().join("|"),
                ),
            )
            contract = compile(
                bindings=(binding,), sources=(source,),
                modules=(register_module(FileModule, FileModuleConfiguration("graph.jsonl")),),
            )
            report = build(contract, output_directory=root / "output")
            self.assertTrue(report.succeeded)
            rows = {
                row["build_key"]: row
                for row in (
                    json.loads(line)
                    for line in (root / "output" / "graph.jsonl")
                    .read_text(encoding="utf-8").splitlines()
                )
            }
            self.assertEqual(
                sorted(rows), ["tagged::a#x,y", "tagged::b#only"]
            )
            a = next(row for row in rows.values() if row["identifier"] == "a")
            b = next(row for row in rows.values() if row["identifier"] == "b")
            self.assertEqual(a["tag_text"], "a|b|c")
            self.assertIsNone(b["tag_text"])

    def test_join_requires_non_null_string_items(self) -> None:
        class Tagged(Table):
            identifier: Field[str] = field()
            codes: Field[Array[str | None]] = field()

        with self.assertRaisesRegex(TypeError, "non-null strings"):
            Tagged.codes.join(",")

        class Raw(Table):
            identifier: Field[str] = field()
            codes: Field[Array[int]] = field()

        with self.assertRaisesRegex(TypeError, "non-null strings"):
            Raw.codes.join(",")

    def test_null_array_items_are_rejected_without_conversion(self) -> None:
        class RawNode(Node):
            codes: PropertySlot[Array[str]] = property()

        class Raw(Table):
            identifier: Field[str] = field()
            codes: Field[Array[str | None]] = field()

        with self.assertRaisesRegex(TypeError, "resolves to"):
            node_binding(
                target=RawNode,
                build_key=Raw.identifier,
                properties=RawNode(codes=Raw.codes),
            )


class NumericKeyTable(Table):
    ordinal: Field[int] = field()
    tag: Field[str] = field()


class NumericKeyNode(Node):
    tag: PropertySlot[str] = property()


class IntTextCastTests(unittest.TestCase):
    """``IntExpression.text()`` lets a numeric member compose a string key."""

    def test_int_member_enters_the_build_key_as_decimal_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "rows.json"
            source_path.write_text(json.dumps([
                {"ordinal": 12, "tag": "x"},
                {"ordinal": 340, "tag": "y"},
            ]), encoding="utf-8")
            source = bind_source(
                target=NumericKeyTable,
                config=DataSourceConfig(str(source_path), format=InputFormat.JSON),
            )
            binding = node_binding(
                target=NumericKeyNode,
                build_key=NumericKeyTable.ordinal.expression.text().prepend("class#"),
                properties=NumericKeyNode(tag=NumericKeyTable.tag),
            )
            contract = compile(
                bindings=(binding,), sources=(source,),
                modules=(register_module(FileModule, FileModuleConfiguration("graph.jsonl")),),
            )
            report = build(contract, output_directory=root / "output")
            self.assertTrue(report.succeeded)
            rows = [
                json.loads(line)
                for line in (root / "output" / "graph.jsonl")
                .read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual({row["build_key"] for row in rows},
                             {"class#12", "class#340"})


class BooleanPredicateTests(unittest.TestCase):
    """A Boolean ``keep_if`` predicate drops rows one product produces."""

    def test_replaced_normalizes_identifier_spaces(self) -> None:
        class CurieNode(Node):
            label: PropertySlot[str] = property()

        class Curie(Table):
            identifier: Field[str] = field()
            label: Field[str] = field()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "curies.json"
            source_path.write_text(json.dumps([
                {"identifier": "HP:0000118", "label": "Migraine"},
            ]), encoding="utf-8")
            source = bind_source(
                target=Curie,
                config=DataSourceConfig(str(source_path), format=InputFormat.JSON),
            )
            binding = node_binding(
                target=CurieNode,
                build_key=Curie.identifier.expression.replaced(":", "_"),
                properties=CurieNode(label=Curie.label),
            )
            contract = compile(
                bindings=(binding,), sources=(source,),
                modules=(register_module(FileModule, FileModuleConfiguration("graph.jsonl")),),
            )
            report = build(contract, output_directory=root / "output")
            self.assertTrue(report.succeeded)
            rows = [
                json.loads(line)
                for line in (root / "output" / "graph.jsonl")
                .read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(rows[0]["build_key"], "HP_0000118")

    def test_split_operators_cut_only_at_the_first_separator(self) -> None:
        class XrefNode(Node):
            key: PropertySlot[str] = property()

        class Xref(Table):
            identifier: Field[str] = field()
            reference: Field[str] = field()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "xrefs.json"
            source_path.write_text(json.dumps([
                {"identifier": "1", "reference": "Wikipedia:Neural_development#Migration"},
                {"identifier": "2", "reference": "OMIM:123456"},
            ]), encoding="utf-8")
            source = bind_source(
                target=Xref,
                config=DataSourceConfig(str(source_path), format=InputFormat.JSON),
            )
            database = Xref.reference.expression.split_before(":")
            payload = Xref.reference.expression.split_after(":")
            binding = node_binding(
                target=XrefNode,
                build_key=database.append("::").append(payload),
                properties=XrefNode(key=database.append("|").append(payload)),
            )
            contract = compile(
                bindings=(binding,), sources=(source,),
                modules=(register_module(FileModule, FileModuleConfiguration("graph.jsonl")),),
            )
            report = build(contract, output_directory=root / "output")
            self.assertTrue(report.succeeded)
            rows = {
                row["build_key"]: row
                for row in (
                    json.loads(line)
                    for line in (root / "output" / "graph.jsonl")
                    .read_text(encoding="utf-8").splitlines()
                )
            }
            self.assertEqual(
                set(rows),
                {
                    "Wikipedia::Neural_development#Migration",
                    "OMIM::123456",
                },
            )

    def test_distinct_projects_repeated_array_items_into_a_set(self) -> None:
        class TagNode(Node):
            key: PropertySlot[str] = property()
            tags: PropertySlot[Array[str]] = property()

        class Tagged(Table):
            identifier: Field[str] = field()
            tags: Field[Array[str | None]] = field()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "tagged.json"
            source_path.write_text(json.dumps([
                {"identifier": "1", "tags": ["b", "a", "b", None]},
            ]), encoding="utf-8")
            source = bind_source(
                target=Tagged,
                config=DataSourceConfig(str(source_path), format=InputFormat.JSON),
            )
            binding = node_binding(
                target=TagNode,
                build_key=Tagged.identifier,
                properties=TagNode(
                    key=Tagged.identifier,
                    tags=Tagged.tags.without_nulls().distinct().sorted(),
                ),
            )
            contract = compile(
                bindings=(binding,), sources=(source,),
                modules=(register_module(FileModule, FileModuleConfiguration("graph.jsonl")),),
            )
            report = build(contract, output_directory=root / "output")
            self.assertTrue(report.succeeded)
            rows = [
                json.loads(line)
                for line in (root / "output" / "graph.jsonl")
                .read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(rows[0]["tags"], ["a", "b"])

    def test_keep_if_becomes_one_true_filter_in_the_where(self) -> None:
        predicate = KeywordInput.keyword_type.expression.equals("TARGET")
        kept = KeywordInput.identifier.expression.keep_if(predicate)
        plan = lower_product(
            {"first": kept.model, "second": kept.model},
            {"keyword_input": "input_relation"},
        )
        # One shared keep_if produces one filter, held as the predicate with mode "true".
        self.assertEqual([filter.mode for filter in plan.filters], ["true"])
        self.assertEqual(plan.filters[0].expression.operator, "equals")
        sql = lower_relation_sql(plan)
        self.assertEqual(sql.count("WHERE"), 1)
        self.assertIn("WHERE", sql)
        self.assertIn('"keyword_type" = \'TARGET\'', sql)
        self.assertNotIn("IS NULL", sql)

    def test_equals_uses_value_semantics_and_can_bind_as_a_property(self) -> None:
        # equals is a plain Boolean value, not a filter: it is not collected as
        # a plan filter unless a keep_if turns it into one.
        predicate = KeywordInput.keyword_type.expression.equals("TARGET")
        plan = lower_product(
            {"match": predicate.model}, {"keyword_input": "input_relation"},
        )
        self.assertEqual(plan.filters, ())
        self.assertIn("= 'TARGET'", lower_relation_sql(plan))

    def test_keep_if_drops_non_matching_rows_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "keywords.json"
            source_path.write_text(json.dumps([
                {"identifier": "keep", "keyword_type": "TARGET",
                 "keywords": [], "optional_keywords": []},
                {"identifier": "drop", "keyword_type": "DISEASE",
                 "keywords": [], "optional_keywords": []},
            ]), encoding="utf-8")
            source = bind_source(
                target=KeywordInput,
                config=DataSourceConfig(str(source_path), format=InputFormat.JSON),
            )
            binding = node_binding(
                target=KeywordNode,
                build_key=KeywordInput.identifier.expression.keep_if(
                    KeywordInput.keyword_type.expression.equals("TARGET")
                ),
                properties=KeywordNode(label=KeywordInput.identifier),
            )
            contract = compile(
                bindings=(binding,), sources=(source,),
                modules=(register_module(
                    FileModule, FileModuleConfiguration("graph.jsonl")
                ),),
            )
            report = build(contract, output_directory=root / "output")
            self.assertTrue(report.succeeded)
            keys = {
                json.loads(line)["build_key"]
                for line in (root / "output" / "graph.jsonl")
                .read_text(encoding="utf-8").splitlines()
            }
            self.assertEqual(keys, {"keep"})


class StructArrayProjectionTests(unittest.TestCase):
    """``map_items`` projects one struct member into a list graph property."""

    def test_map_items_builds_a_list_property_including_a_null_array(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "keywords.json"
            source_path.write_text(json.dumps([
                {"identifier": "a", "keyword_type": "t",
                 "keywords": [{"keyword_id": "k1", "keyword_type": "t"},
                              {"keyword_id": "k2", "keyword_type": "t"}],
                 "optional_keywords": None},
                {"identifier": "b", "keyword_type": "t",
                 "keywords": [{"keyword_id": "k3", "keyword_type": "t"}],
                 "optional_keywords": [{"keyword_id": "k4", "keyword_type": "t"}]},
            ]), encoding="utf-8")
            source = bind_source(
                target=KeywordInput,
                config=DataSourceConfig(str(source_path), format=InputFormat.JSON),
            )
            binding = node_binding(
                target=KeywordCollectionNode,
                build_key=KeywordInput.identifier,
                properties=KeywordCollectionNode(
                    ids=KeywordInput.keywords.map_items(lambda item: item.keyword_id),
                    optional_ids=KeywordInput.optional_keywords.map_items(
                        lambda item: item.keyword_id
                    ),
                ),
            )
            contract = compile(
                bindings=(binding,), sources=(source,),
                modules=(register_module(
                    FileModule, FileModuleConfiguration("graph.jsonl")
                ),),
            )
            report = build(contract, output_directory=root / "output")
            self.assertTrue(report.succeeded)
            rows = {
                row["build_key"]: row
                for row in (
                    json.loads(line)
                    for line in (root / "output" / "graph.jsonl")
                    .read_text(encoding="utf-8").splitlines()
                )
            }
            self.assertEqual(rows["a"]["ids"], ["k1", "k2"])
            self.assertIsNone(rows["a"]["optional_ids"], "a null array maps to a null list")
            self.assertEqual(rows["b"]["ids"], ["k3"])
            self.assertEqual(rows["b"]["optional_ids"], ["k4"])

    def test_map_items_of_a_null_member_yields_a_null_item_dropped_by_without_nulls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "notes.json"
            source_path.write_text(json.dumps([
                {"identifier": "a",
                 "keywords": [{"keyword_id": "k1", "note": "keep"},
                              {"keyword_id": "k2", "note": None}]},
            ]), encoding="utf-8")
            source = bind_source(
                target=NullableKeywordInput,
                config=DataSourceConfig(str(source_path), format=InputFormat.JSON),
            )
            binding = node_binding(
                target=NullableMemberNode,
                build_key=NullableKeywordInput.identifier,
                properties=NullableMemberNode(
                    notes=NullableKeywordInput.keywords.map_items(
                        lambda item: item.note
                    ).without_nulls(),
                ),
            )
            contract = compile(
                bindings=(binding,), sources=(source,),
                modules=(register_module(
                    FileModule, FileModuleConfiguration("graph.jsonl")
                ),),
            )
            report = build(contract, output_directory=root / "output")
            self.assertTrue(report.succeeded)
            rows = [
                json.loads(line)
                for line in (root / "output" / "graph.jsonl")
                .read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(rows[0]["notes"], ["keep"])


if __name__ == "__main__":
    unittest.main()
