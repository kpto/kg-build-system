from __future__ import annotations

import datetime
import json
import tempfile
import unittest
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

from kg_build_system import (
    Array, BuildRuntime, DataSourceConfig, Field, InputFormat, Node, NodeValues,
    Projection, PropertySlot, Struct, Table, bind_source, build, compile,
    create_blueprint, field, node_binding, computed_field, property,
)
from kg_build_system._frozen_json import freeze_json
from kg_build_system.expressions import value_expression
from kg_build_system.types import Date
from kg_build_system.modules import (
    CollapseExactDuplicatesModule, FileModule, FileModuleConfiguration,
    MergeCompatibleFactsModule, MergeCompatibleFactsModuleConfiguration,
    register_module,
)
from kg_build_system.modules.core.credentials import configure_source_credentials
from kg_build_system.modules.core.core import CoreArtifactTypes
from kg_build_system.modules.targets.file import FileExecutor
from kg_build_system.relational import lower_product
from kg_build_system.engines.duckdb import lower_relation_sql
from kg_build_system.workflow.identity import (
    expanded_input_name, opening_identity, step_identity,
)
from kg_build_system.workflow.ir import WorkflowContractIR
from kg_build_system.workflow.models import (
    Artifact, ArtifactType, ContinuableInput, DefinedStep, ExecutionContext,
    ModuleDefinition, ModuleReference, Publication, StepStatus, TakenInput,
)
from kg_build_system.workflow.services import RelationRef


class LoweringEvidence(Struct):
    labels: Field[Array[str]] = field()


class LoweringInput(Table):
    identifier: Field[str] = field()
    optional_label: Field[str | None] = field()
    evidence: Field[Array[LoweringEvidence]] = field()


class LoweringProjection(Projection(LoweringInput.row_source())):
    identifier = computed_field(LoweringInput.identifier)
    label = computed_field(
        LoweringInput.evidence.alter_rows().expand()
        .extract(lambda item: item.labels)
        .alter_rows().expand()
        .expression.append("!")
    )


class LoweringNode(Node):
    label: PropertySlot[str] = property()


class MergeInput(Table):
    identifier: Field[str] = field()
    value: Field[int] = field()


class MergeANode(Node):
    value: PropertySlot[int] = property()


class MergeBNode(Node):
    value: PropertySlot[int] = property()


class TransformInner(Struct):
    value: Field[str] = field()


class TransformDetail(Struct):
    code: Field[str] = field()
    inner: Field[TransformInner] = field()
    tags: Field[Array[str]] = field()


class TransformInput(Table):
    identifier: Field[str] = field()
    details: Field[Array[TransformDetail]] = field()
    tags: Field[Array[str | None]] = field()
    numbers: Field[Array[int]] = field()


class TransformNode(Node):
    codes: PropertySlot[Array[str]] = property()
    labels: PropertySlot[Array[str]] = property()
    nested: PropertySlot[Array[str]] = property()
    numbers: PropertySlot[Array[int]] = property()
    number_text: PropertySlot[Array[str]] = property()
    tags: PropertySlot[str] = property()


def core_instructions(contract: WorkflowContractIR) -> dict[str, dict[str, Any]]:
    """The instruction core ships for each of its steps, keyed by step name.

    A step carries no data of its own, so what core's executor runs for a step is
    filed under that step's name inside core's own variables.
    """
    core = next(
        item for item in contract.workflow.contributions
        if item.reference.module_id == "core"
    )
    variables = cast(dict[str, Any], core.variables)
    return cast(dict[str, dict[str, Any]], variables["instructions"])


def file_records_input(component: str) -> str:
    """The identity of the file target's opening that takes one component's records."""
    return opening_identity(
        step_identity(FileModule.ID, "write"),
        expanded_input_name("records", CoreArtifactTypes.graph_records("node", component)),
    )


class RelationalLoweringTests(unittest.TestCase):
    def test_nested_expansions_are_parent_first_and_shared(self) -> None:
        first = (
            LoweringInput.evidence.alter_rows().expand()
            .extract(lambda item: item.labels)
            .alter_rows().expand()
            .expression.append("!")
        )
        plan = lower_product(
            {
                "first": first.model,
                "second": first.model,
                "present": LoweringInput.optional_label.alter_rows().drop_null().expression.model,
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
            build_key=LoweringProjection.identifier.alter_rows().drop_null(),
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
        self.assertEqual(contract_document["schema_version"], 2)
        self.assertEqual(
            contract_document["provenance"]["compile"]["blueprint"]["schema_version"],
            blueprint.schema_version,
        )
        self.assertNotIn("blueprint", contract_document)
        contributions = contract_document["workflow"]["contributions"]
        self.assertTrue(all(
            "priority" not in contribution["reference"]
            for contribution in contributions
        ))
        self.assertTrue(all(
            "assembly_preference" not in step
            for contribution in contributions
            for step in contribution["steps"]
        ))
        projection_sql = core_instructions(contract)[
            f"projection.{blueprint.projections[0].name}"
        ]["sql"]
        self.assertEqual(str(projection_sql).count("UNNEST"), 2)

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
            build_key=LoweringProjection.identifier.alter_rows().drop_null(),
            properties=LoweringNode(label=LoweringProjection.label),
        )
        contract = compile(
            bindings=(binding,), sources=(source,),
            modules=(register_module(
                FileModule, FileModuleConfiguration("graph.jsonl")
            ),),
        )
        # The source step carries what the contract knows about the contract, so
        # the shape check and the null-count pre-flight can run without a
        # blueprint. Only paths the build reads that claim non-nullity are listed:
        # a read of an expanded array reaches the members below it, and a Parquet
        # path carries one pair of list wrappers per array level crossed.
        self.assertEqual(core_instructions(contract)["table.lowering_input"], {
            "action": "source_relation",
            "relation": "kg_table_0",
            "location": "s3://bucket/input.json",
            "format": "json",
            "credential_reference": "source_credentials",
            "declaration": "lowering_input",
            "declared_columns": [
                {"name": "identifier", "logical_type": {"kind": "unit", "name": "str"}},
                {"name": "optional_label", "logical_type": {"kind": "unit", "name": "str"}},
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
                build_key=LoweringProjection.identifier.alter_rows().drop_null(),
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
            build_key=LoweringProjection.identifier.alter_rows().drop_null(),
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
            connection.output_id
            for connection in contract.workflow.connections
            if connection.input_id == file_records_input("lowering")
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
        survey = CoreArtifactTypes.graph_records("node", "survey")
        records = Artifact("output", survey, RelationRef("kg_records"))

        FileExecutor({}).handle(ExecutionContext(
            module=ModuleDefinition(ModuleReference(
                module_id=FileModule.ID,
                import_module=FileModule.__module__,
                class_qualname=FileModule.__qualname__,
                implementation_version=FileModule.VERSION,
                configuration=freeze_json({"relative_path": "graph.jsonl"}),
            )),
            step=DefinedStep(
                name="write",
                inputs=(TakenInput(
                    type=survey,
                    name=expanded_input_name("records", survey),
                    input_name="records",
                ),),
                outputs=(Publication(
                    ArtifactType(FileModule.ID, "write_result"), "result",
                ),),
            ),
            module_id=FileModule.ID,
            step_id=step_identity(FileModule.ID, "write"),
            variables={},
            runtime_configuration={},
            # A running step receives its inputs under the input it declared,
            # which for an open input names every port that grew from it.
            inputs={"records": (ContinuableInput(
                output_id=opening_identity(
                    step_identity("core", "aggregate.survey"), "output",
                ),
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


class MergeScopeTests(unittest.TestCase):
    def _binding(self, target):
        return node_binding(
            target=target,
            rows=MergeInput,
            bind=lambda row: NodeValues(
                build_key=row.identifier.alter_rows().drop_null(),
                properties=target(value=row.value.alter_rows().drop_null()),
            ),
        )

    def test_configuration_takes_component_classes(self) -> None:
        config = MergeCompatibleFactsModuleConfiguration(
            components=(MergeANode,),
        )
        self.assertEqual(
            config.to_json(),
            {"components": [{
                "module": MergeANode.__module__,
                "qualname": MergeANode.__qualname__,
            }]},
        )
        with self.assertRaisesRegex(TypeError, "concrete Node or Edge"):
            MergeCompatibleFactsModuleConfiguration(
                components=("merge_a",),  # type: ignore[arg-type]
            )

    def test_only_the_named_component_folds_duplicate_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "rows.json"
            data.write_text(json.dumps([
                {"identifier": "x", "value": 2},
                {"identifier": "x", "value": 1},
            ]), encoding="utf-8")
            source = bind_source(
                target=MergeInput,
                config=DataSourceConfig(str(data), format=InputFormat.JSON),
            )
            contract = compile(
                bindings=(self._binding(MergeANode), self._binding(MergeBNode)),
                sources=(source,),
                modules=(
                    register_module(
                        MergeCompatibleFactsModule,
                        MergeCompatibleFactsModuleConfiguration(
                            components=(MergeANode,),
                        ),
                    ),
                    register_module(
                        FileModule, FileModuleConfiguration("graph.jsonl"),
                    ),
                ),
            )
            report = build(contract, output_directory=root / "output")
            self.assertTrue(report.succeeded)
            rows = [
                json.loads(line)
                for line in (root / "output" / "graph.jsonl")
                .read_text(encoding="utf-8").splitlines()
            ]

        a_rows = [row for row in rows if row["type"] == "merge_a"]
        b_rows = [row for row in rows if row["type"] == "merge_b"]
        self.assertEqual([row["value"] for row in a_rows], [1])
        self.assertEqual(sorted(row["value"] for row in b_rows), [1, 2])


class ArrayTransformTests(unittest.TestCase):
    def test_transform_items_and_array_operators_build(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "details.json"
            source_path.write_text(json.dumps([{
                "identifier": "a",
                "details": [
                    {"code": "x", "inner": {"value": "one"}, "tags": []},
                    {"code": "y", "inner": {"value": "two"}, "tags": []},
                ],
                "tags": ["b", None, "a", "b"],
                "numbers": [1, 2],
            }]), encoding="utf-8")
            source = bind_source(
                target=TransformInput,
                config=DataSourceConfig(str(source_path), format=InputFormat.JSON),
            )
            codes = TransformInput.details.alter_rows().drop_null().transform_items(
                lambda item: item.extract(lambda detail: detail.code).default_to("").expression
            )
            nested = TransformInput.details.alter_rows().drop_null().transform_items(
                lambda item: item.extract(lambda detail: detail.inner)
                .extract(lambda inner: inner.value).default_to("").expression
            )
            labels = TransformInput.details.alter_rows().drop_null().transform_items(
                lambda item: item.extract(lambda detail: detail.code).default_to("")
                .expression.append("!")
            )
            numbers = TransformInput.details.alter_rows().drop_null().transform_items(
                lambda _: value_expression(7)
            )
            number_text = TransformInput.numbers.alter_rows().drop_null().transform_items(
                lambda item: item.to_string()
            )
            tags = (
                TransformInput.tags.alter_rows().drop_null().drop_null_items()
                .unique().sort().concat("|")
            )
            binding = node_binding(
                target=TransformNode,
                build_key=TransformInput.identifier.alter_rows().drop_null(),
                properties=TransformNode(
                    codes=codes, labels=labels, nested=nested,
                    numbers=numbers, number_text=number_text, tags=tags,
                ),
            )
            contract = compile(
                bindings=(binding,),
                sources=(source,),
                modules=(register_module(
                    FileModule, FileModuleConfiguration("graph.jsonl"),
                ),),
            )
            report = build(contract, output_directory=root / "output")
            self.assertTrue(report.succeeded)
            row = json.loads(
                (root / "output" / "graph.jsonl")
                .read_text(encoding="utf-8").splitlines()[0]
            )

        self.assertEqual(row["codes"], ["x", "y"])
        self.assertEqual(row["labels"], ["x!", "y!"])
        self.assertEqual(row["nested"], ["one", "two"])
        self.assertEqual(row["numbers"], [7, 7])
        self.assertEqual(row["number_text"], ["1", "2"])
        self.assertEqual(row["tags"], "a|b")

    def test_transform_items_rejects_a_raw_literal(self) -> None:
        with self.assertRaisesRegex(TypeError, "value selection or value expression"):
            TransformInput.details.alter_rows().drop_null().transform_items(lambda _: 7)

    def test_transform_items_rejects_a_row_effect(self) -> None:
        with self.assertRaisesRegex(TypeError, "row effects"):
            TransformInput.details.alter_rows().drop_null().transform_items(
                lambda item: item.extract(lambda detail: detail.tags)
                .alter_rows().expand().expression
            )

    def test_join_requires_non_null_string_items(self) -> None:
        with self.assertRaisesRegex(TypeError, "non-null strings"):
            TransformInput.tags.alter_rows().drop_null().expression.join("|")
        with self.assertRaisesRegex(TypeError, "non-null strings"):
            TransformInput.details.alter_rows().drop_null().expression.join("|")


class ArrayPropertyTests(unittest.TestCase):
    """A flat, non-null scalar array is a first-class graph property."""

    def test_flat_scalar_array_builds_to_a_json_property(self) -> None:
        class TaggedNode(Node):
            codes: PropertySlot[Array[str]] = property()
            optional_codes: PropertySlot[Array[str] | None] = property()

        class Tagged(Table):
            identifier: Field[str] = field()
            codes: Field[Array[str]] = field()
            optional_codes: Field[Array[str] | None] = field()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "tagged.json"
            source_path.write_text(json.dumps([
                {"identifier": "a", "codes": ["x", "y"], "optional_codes": None},
                {"identifier": "b", "codes": ["z"], "optional_codes": ["p", "q"]},
            ]), encoding="utf-8")
            source = bind_source(
                target=Tagged,
                config=DataSourceConfig(str(source_path), format=InputFormat.JSON),
            )
            binding = node_binding(
                target=TaggedNode,
                build_key=Tagged.identifier.alter_rows().drop_null(),
                properties=TaggedNode(
                    codes=Tagged.codes.alter_rows().drop_null(),
                    optional_codes=Tagged.optional_codes,
                ),
            )
            contract = compile(
                bindings=(binding,),
                sources=(source,),
                modules=(register_module(
                    FileModule, FileModuleConfiguration("graph.jsonl"),
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

        self.assertEqual(rows["a"]["codes"], ["x", "y"])
        self.assertIsNone(rows["a"]["optional_codes"])
        self.assertEqual(rows["b"]["codes"], ["z"])
        self.assertEqual(rows["b"]["optional_codes"], ["p", "q"])

    def test_nested_array_property_is_refused(self) -> None:
        with self.assertRaisesRegex(TypeError, "require scalar items"):
            class Nested(Node):
                codes: PropertySlot[Array[Array[str]]] = property()  # type: ignore[valid-type]

    def test_struct_array_property_is_refused(self) -> None:
        with self.assertRaisesRegex(TypeError, "require scalar items"):
            class Structured(Node):
                evidence: PropertySlot[Array[LoweringEvidence]] = property()

    def test_nullable_array_items_are_refused(self) -> None:
        with self.assertRaisesRegex(TypeError, "require non-null items"):
            class NullableItems(Node):
                codes: PropertySlot[Array[str | None]] = property()

    def test_temporal_array_items_are_a_legal_declaration(self) -> None:
        from kg_build_system.types import ArrayType, UnitType

        class TemporalItems(Node):
            dates: PropertySlot[Array[Date]] = property()

        declaration = TemporalItems._properties["dates"]
        self.assertEqual(declaration.logical_type, ArrayType(UnitType("date")))

    def test_binding_sql_casts_properties_to_the_declared_type(self) -> None:
        class DatedInput(Table):
            identifier: Field[str] = field()
            dates: Field[Array[Date] | None] = field()

        class DatedNode(Node):
            dates: PropertySlot[Array[Date] | None] = property()

        binding = node_binding(
            target=DatedNode,
            build_key=DatedInput.identifier.alter_rows().drop_null(),
            properties=DatedNode(dates=DatedInput.dates),
        )
        contract = compile(
            bindings=(binding,),
            sources=(bind_source(
                target=DatedInput,
                config=DataSourceConfig("input.json", format=InputFormat.JSON),
            ),),
            modules=(register_module(
                FileModule, FileModuleConfiguration("graph.jsonl"),
            ),),
        )
        instructions = core_instructions(contract)
        binding_sql = next(
            item["sql"] for name, item in instructions.items()
            if name.startswith("binding.")
        )
        self.assertIn('CAST("dates" AS DATE[]) AS "_kg_raw_dates"', binding_sql)


class SeparatorOperationTests(unittest.TestCase):
    def test_text_lowers_scalars_to_canonical_sql(self) -> None:
        integer_sql = lower_relation_sql(lower_product(
            {"value": value_expression(12).to_string().model}, {},
        ))
        self.assertRegex(integer_sql, r"CAST\(12 AS (TEXT|VARCHAR)\)")

        timestamp_sql = lower_relation_sql(lower_product(
            {"value": value_expression(
                datetime.datetime(2026, 7, 14, 6, 15),
            ).to_string().model}, {},
        ))
        self.assertIn("REPLACE(CAST(", timestamp_sql)
        self.assertIn("' '", timestamp_sql)
        self.assertIn("'T'", timestamp_sql)

    def test_equals_lowers_to_a_boolean_comparison(self) -> None:
        expression = value_expression("target").equals("target")
        sql = lower_relation_sql(lower_product({"value": expression.model}, {}))
        self.assertIn("'target' = 'target'", sql)

    def test_before_and_after_take_the_nth_separator(self) -> None:
        class XrefNode(Node):
            label: PropertySlot[str] = property()

        class Xref(Table):
            identifier: Field[str] = field()
            reference: Field[str] = field()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "xrefs.json"
            source_path.write_text(json.dumps([
                {"identifier": "1", "reference": "Wikipedia:Neural:Migration"},
                {"identifier": "2", "reference": "OMIM:123456"},
            ]), encoding="utf-8")
            source = bind_source(
                target=Xref,
                config=DataSourceConfig(str(source_path), format=InputFormat.JSON),
            )
            before = Xref.reference.alter_rows().drop_null().expression.before_separator(":", 2)
            after = Xref.reference.alter_rows().drop_null().expression.after_separator(":", 2)
            binding = node_binding(
                target=XrefNode,
                build_key=before.append("|").append(after),
                properties=XrefNode(
                    label=Xref.reference.alter_rows().drop_null().expression.replace(":", "_"),
                ),
            )
            contract = compile(
                bindings=(binding,),
                sources=(source,),
                modules=(register_module(
                    FileModule, FileModuleConfiguration("graph.jsonl"),
                ),),
            )
            report = build(contract, output_directory=root / "output")
            self.assertTrue(report.succeeded)
            rows = {
                row["build_key"]: row["label"]
                for row in (
                    json.loads(line)
                    for line in (root / "output" / "graph.jsonl")
                    .read_text(encoding="utf-8").splitlines()
                )
            }

        self.assertEqual(
            rows,
            {
                "Wikipedia:Neural|Migration": "Wikipedia_Neural_Migration",
                "OMIM:123456|": "OMIM_123456",
            },
        )

    def test_include_separator_preserves_the_cut_separator(self) -> None:
        class XrefNode(Node):
            left: PropertySlot[str] = property()
            right: PropertySlot[str] = property()

        class Xref(Table):
            identifier: Field[str] = field()
            reference: Field[str] = field()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "xrefs.json"
            source_path.write_text(json.dumps([
                {"identifier": "1", "reference": "Wikipedia:Neural:Migration"},
            ]), encoding="utf-8")
            source = bind_source(
                target=Xref,
                config=DataSourceConfig(str(source_path), format=InputFormat.JSON),
            )
            binding = node_binding(
                target=XrefNode,
                build_key=Xref.identifier.alter_rows().drop_null(),
                properties=XrefNode(
                    left=Xref.reference.alter_rows().drop_null().expression.before_separator(
                        ":", 1, include_separator=True,
                    ),
                    right=Xref.reference.alter_rows().drop_null().expression.after_separator(
                        ":", 1, include_separator=True,
                    ),
                ),
            )
            contract = compile(
                bindings=(binding,),
                sources=(source,),
                modules=(register_module(
                    FileModule, FileModuleConfiguration("graph.jsonl"),
                ),),
            )
            report = build(contract, output_directory=root / "output")
            self.assertTrue(report.succeeded)
            row = json.loads(
                (root / "output" / "graph.jsonl")
                .read_text(encoding="utf-8").splitlines()[0]
            )

        self.assertEqual(row["left"], "Wikipedia:")
        self.assertEqual(row["right"], ":Neural:Migration")


if __name__ == "__main__":
    unittest.main()
