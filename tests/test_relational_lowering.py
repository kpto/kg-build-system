from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from kg_build_system import (
    Array, DataSourceConfig, Field, InputFormat, Node, Projection, PropertySlot,
    Struct, Table, bind_source, build, compile, create_blueprint,
    field, node_binding, projection_field, property,
)
from kg_build_system.compile.contracts import BuildContract
from kg_build_system.modules import (
    CollapseExactDuplicatesModule, FileModule, FileModuleConfiguration,
    MergeCompatibleFactsModule,
)
from kg_build_system.modules.core.credentials import configure_source_credentials
from kg_build_system.relational import lower_product
from kg_build_system.engines.duckdb import lower_relation_sql


class LoweringEvidence(Struct):
    labels: Field[Array[str]] = field()


class LoweringInput(Table):
    identifier: Field[str] = field()
    optional_label: Field[str | None] = field()
    evidence: Field[Array[LoweringEvidence]] = field()


class LoweringProjection(Projection):
    identifier = projection_field(LoweringInput.identifier)
    label = projection_field(
        LoweringInput.evidence.each()
        .pick(lambda item: item.labels)
        .each()
        .append("!")
    )


class LoweringNode(Node):
    label: PropertySlot[str] = property()


class RelationalLoweringTests(unittest.TestCase):
    def test_nested_expansions_are_parent_first_and_shared(self) -> None:
        first = (
            LoweringInput.evidence.each()
            .pick(lambda item: item.labels)
            .each()
            .append("!")
        )
        plan = lower_product(
            {
                "first": first.expression,
                "second": first.expression,
                "present": LoweringInput.optional_label.when_present().expression,
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
            modules=(FileModule(FileModuleConfiguration("graph.jsonl")),),
        )
        self.assertEqual(
            tuple(module.module_id for module in blueprint.modules),
            (FileModule.ID, "core"),
        )
        contract = compile(blueprint=blueprint)
        restored = BuildContract.model_validate_json(contract.model_dump_json())
        self.assertEqual(restored.blueprint, blueprint)
        self.assertEqual(restored.workflow, contract.workflow)
        contract_document = json.loads(contract.model_dump_json())
        self.assertEqual(contract_document["schema_version"], 1)
        self.assertNotIn("sources", contract_document)
        self.assertNotIn("overrides", contract_document)
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
        contract = compile(bindings=(binding,), sources=(source,))
        source_step = next(
            step for step in contract.workflow.steps
            if step.step_id == "core::table.lowering_input"
        )
        self.assertEqual(source_step.payload, {
            "action": "source_relation",
            "relation": "kg_table_0",
            "location": "s3://bucket/input.json",
            "format": "json",
            "credential_reference": "source_credentials",
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
        services.duckdb.register_filesystem.assert_called_once_with(filesystem)

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
                    FileModule(FileModuleConfiguration("graph.jsonl")),
                    CollapseExactDuplicatesModule(),
                ),
            )
            report = build(
                contract,
                output_directory=root / "output",
            )
            self.assertTrue(report.succeeded)
            rows = [
                json.loads(line)
                for line in (root / "output" / "graph.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(sorted(row["label"] for row in rows), ["one!", "two!"])
            self.assertEqual(len(report.published_artifacts), 1)

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
                FileModule(FileModuleConfiguration("graph.jsonl")),
                MergeCompatibleFactsModule(),
                CollapseExactDuplicatesModule(),
            ),
        )
        contract = compile(blueprint=blueprint)
        file_outputs = {
            connection.output_slot_id
            for connection in contract.workflow.connections
            if connection.input_slot_id == "file::write.records"
        }
        self.assertEqual(len(file_outputs), 1)
        self.assertTrue(
            next(iter(file_outputs)).startswith("collapse_exact_duplicates::")
        )


if __name__ == "__main__":
    unittest.main()
