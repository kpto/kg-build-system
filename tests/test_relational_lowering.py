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
    MergeCompatibleFactsModule, register_module,
)
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


if __name__ == "__main__":
    unittest.main()
