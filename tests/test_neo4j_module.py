from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import duckdb

from kg_build_system import (
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
from kg_build_system._frozen_json import thaw_json
from kg_build_system.modules import (
    Neo4jModule,
    Neo4jModuleConfiguration,
    register_module,
)
from kg_build_system.modules.targets.neo4j.ir import (
    Neo4jExportInstructionIR,
    Neo4jScriptInstructionIR,
    decode_neo4j_instruction,
)


class Neo4jInput(Table):
    identifier: Field[str] = field()
    friend_identifier: Field[str] = field()
    name: Field[str] = field()
    weight: Field[int] = field()


class PersonNode(Node):
    options = NodeOptions(annotations=(NodeLabel("Person"),))

    name: PropertySlot[str] = property()


class KnowsEdge(Edge[PersonNode, PersonNode]):
    options = EdgeOptions(annotations=(EdgeLabel("KNOWS"),))

    weight: PropertySlot[int] = property()


person_binding = node_binding(
    target=PersonNode,
    build_key=Neo4jInput.identifier,
    properties=PersonNode(name=Neo4jInput.name),
)
knows_binding = edge_binding(
    target=KnowsEdge,
    build_key=(
        Neo4jInput.identifier.expression
        .append("::")
        .append(Neo4jInput.friend_identifier.expression)
    ),
    source_build_key=Neo4jInput.identifier,
    target_build_key=Neo4jInput.friend_identifier,
    properties=KnowsEdge(weight=Neo4jInput.weight),
)


def _source(path: Path):
    return bind_source(
        target=Neo4jInput,
        config=DataSourceConfig(str(path), format=InputFormat.JSON),
    )


class LabelAnnotationTests(unittest.TestCase):
    def test_labels_are_portable_topology_annotations(self) -> None:
        blueprint = create_blueprint(bindings=(person_binding, knows_binding))
        labels = {
            component.kind: (
                component.annotations[0].namespace,
                component.annotations[0].annotation_id,
                thaw_json(component.annotations[0].arguments),
            )
            for component in blueprint.components
        }
        self.assertEqual(
            labels["node"],
            ("kg_build_system.topology", "node_label", {"label": "Person"}),
        )
        self.assertEqual(
            labels["edge"],
            ("kg_build_system.topology", "edge_label", {"label": "KNOWS"}),
        )

    def test_rejects_empty_labels(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty"):
            NodeLabel("  ")

    def test_neo4j_compiler_uses_computed_names_without_annotations(self) -> None:
        class DefaultNode(Node):
            options = NodeOptions(name="ENTITY")

            name: PropertySlot[str] = property()

        class DefaultEdge(Edge[DefaultNode, DefaultNode]):
            options = EdgeOptions(name="IS_A")

            weight: PropertySlot[int] = property()

        default_node = node_binding(
            target=DefaultNode,
            build_key=Neo4jInput.identifier,
            properties=DefaultNode(name=Neo4jInput.name),
        )
        default_edge = edge_binding(
            target=DefaultEdge,
            build_key=Neo4jInput.identifier,
            source_build_key=Neo4jInput.identifier,
            target_build_key=Neo4jInput.friend_identifier,
            properties=DefaultEdge(weight=Neo4jInput.weight),
        )
        contract = compile(
            bindings=(default_node, default_edge),
            sources=(_source(Path("input.json")),),
            modules=(register_module(Neo4jModule),),
        )
        instructions = tuple(
            instruction
            for step in contract.workflow.steps
            if step.module_id == Neo4jModule.ID
            for instruction in (decode_neo4j_instruction(step.payload),)
            if isinstance(instruction, Neo4jExportInstructionIR)
        )
        self.assertEqual(
            {
                instruction.component.kind: instruction.component.label
                for instruction in instructions
            },
            {"node": "ENTITY", "edge": "IS_A"},
        )

    def test_neo4j_compiler_rejects_multiple_labels(self) -> None:
        class AmbiguousNode(Node):
            options = NodeOptions(
                annotations=(NodeLabel("First"), NodeLabel("Second")),
            )

            name: PropertySlot[str] = property()

        binding = node_binding(
            target=AmbiguousNode,
            build_key=Neo4jInput.identifier,
            properties=AmbiguousNode(name=Neo4jInput.name),
        )
        with self.assertRaisesRegex(ValueError, "at most one NodeLabel"):
            compile(
                bindings=(binding,),
                sources=(_source(Path("input.json")),),
                modules=(register_module(Neo4jModule),),
            )


class Neo4jTargetTests(unittest.TestCase):
    def test_compiles_one_export_per_component_then_the_script(self) -> None:
        contract = compile(
            bindings=(person_binding, knows_binding),
            sources=(_source(Path("input.json")),),
            modules=(register_module(Neo4jModule),),
        )
        neo4j_steps = tuple(
            step for step in contract.workflow.steps
            if step.module_id == Neo4jModule.ID
        )
        export_steps = tuple(
            step for step in neo4j_steps
            if isinstance(
                decode_neo4j_instruction(step.payload),
                Neo4jExportInstructionIR,
            )
        )
        export_instructions = tuple(
            instruction
            for step in export_steps
            for instruction in (decode_neo4j_instruction(step.payload),)
            if isinstance(instruction, Neo4jExportInstructionIR)
        )
        script_step = neo4j_steps[-1]
        script_instruction = decode_neo4j_instruction(script_step.payload)

        self.assertEqual(len(export_steps), 2)
        self.assertEqual(
            {
                instruction.component.component
                for instruction in export_instructions
            },
            {"person", "knows"},
        )
        self.assertEqual(script_step.step_id, "neo4j::script")
        self.assertIsInstance(script_instruction, Neo4jScriptInstructionIR)

        output_owner = {
            output.slot_id: step.step_id
            for step in contract.workflow.steps
            for output in step.outputs
        }
        export_dependencies = {
            step.step_id: {
                output_owner[connection.output_slot_id]
                for connection in contract.workflow.connections
                if connection.input_slot_id == step.inputs[0].slot_id
            }
            for step in export_steps
        }
        self.assertTrue(all(
            len(dependencies) == 1
            and next(iter(dependencies)).startswith("core::aggregate.")
            for dependencies in export_dependencies.values()
        ))
        script_input = script_step.inputs[0].slot_id
        script_dependencies = {
            output_owner[connection.output_slot_id]
            for connection in contract.workflow.connections
            if connection.input_slot_id == script_input
        }
        self.assertEqual(
            script_dependencies,
            {step.step_id for step in export_steps},
        )

    def test_writes_import_header_parquet_and_standalone_script(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "input.json"
            data.write_text(json.dumps([
                {
                    "identifier": "person-1",
                    "friend_identifier": "person-2",
                    "name": "Ada",
                    "weight": 7,
                },
                {
                    "identifier": "person-2",
                    "friend_identifier": "person-1",
                    "name": "Grace",
                    "weight": 9,
                },
            ]), encoding="utf-8")
            output = root / "output"
            contract = compile(
                bindings=(person_binding, knows_binding),
                sources=(_source(data),),
                modules=(register_module(
                    Neo4jModule,
                    Neo4jModuleConfiguration(relative_directory="neo4j"),
                ),),
            )
            report = build(contract, output_directory=output)

            self.assertTrue(report.succeeded)
            self.assertEqual(len(report.published_artifacts), 1)
            summary = report.published_artifacts[0].value
            self.assertEqual(summary["nodes"], 2)
            self.assertEqual(summary["edges"], 2)
            self.assertEqual(len(summary["node_files"]), 1)
            self.assertEqual(len(summary["relationship_files"]), 1)

            bundle = output / "neo4j"
            node_path = bundle / summary["node_files"][0]
            edge_path = bundle / summary["relationship_files"][0]
            connection = duckdb.connect(":memory:")
            node_query = connection.execute(
                "SELECT * FROM read_parquet(?) ORDER BY name", [str(node_path)]
            )
            node_columns = tuple(item[0] for item in node_query.description)
            node_rows = node_query.fetchall()
            self.assertRegex(node_columns[0], r"^build_key:ID\(kg_[0-9a-f]{16}\)$")
            self.assertEqual(node_columns[1:], ("name", ":LABEL"))
            self.assertEqual(
                node_rows,
                [("person-1", "Ada", "Person"), ("person-2", "Grace", "Person")],
            )

            id_match = re.fullmatch(r"build_key:ID\((.+)\)", node_columns[0])
            assert id_match is not None
            id_space = id_match.group(1)
            edge_query = connection.execute(
                'SELECT * FROM read_parquet(?) ORDER BY "build_key"', [str(edge_path)]
            )
            edge_columns = tuple(item[0] for item in edge_query.description)
            edge_rows = edge_query.fetchall()
            self.assertEqual(edge_columns, (
                "build_key",
                f":START_ID({id_space})",
                f":END_ID({id_space})",
                "weight",
                ":TYPE",
            ))
            self.assertEqual(edge_rows, [
                ("person-1::person-2", "person-1", "person-2", 7, "KNOWS"),
                ("person-2::person-1", "person-2", "person-1", 9, "KNOWS"),
            ])

            script = bundle / "import_neo4j.py"
            self.assertTrue(script.is_file())
            fake_admin = root / (
                "neo4j-admin.bat" if os.name == "nt" else "neo4j-admin"
            )
            fake_admin.write_text("", encoding="utf-8")
            if os.name != "nt":
                fake_admin.chmod(0o755)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "knowledge",
                    "--neo4j-admin",
                    str(fake_admin),
                    "--print-command",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            command = completed.stdout.strip()
            self.assertIn("database import full knowledge", command)
            self.assertIn("--input-type=parquet", command)
            self.assertIn(f"--nodes={node_path}", command)
            self.assertIn(f"--relationships={edge_path}", command)

    def test_configuration_rejects_escaping_paths(self) -> None:
        with self.assertRaisesRegex(ValueError, "relative"):
            Neo4jModuleConfiguration(relative_directory="../outside")

    def test_compile_rejects_edges_without_bound_endpoint_nodes(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires bound source and target"):
            compile(
                bindings=(knows_binding,),
                sources=(_source(Path("input.json")),),
                modules=(register_module(Neo4jModule),),
            )


if __name__ == "__main__":
    unittest.main()
