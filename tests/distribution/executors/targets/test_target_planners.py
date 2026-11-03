from __future__ import annotations

import hashlib
import unittest

from kg_build_system.distribution.executors.file import (
    FileConfiguration,
    FilePlanner,
)
from kg_build_system.distribution.executors.meta_graph import (
    MetaGraphConfiguration,
    MetaGraphPlanner,
)
from kg_build_system.distribution.executors.neo4j import (
    Neo4jConfiguration,
    Neo4jPlanner,
)
from kg_build_system.kernel import (
    ArtifactType,
    Input,
    Output,
    PlanContext,
    Publication,
    RuntimeField,
)

from ._support import bound_blueprint, node


class FilePlannerTests(unittest.TestCase):
    def test_the_file_planner_emits_its_one_deferred_step(self) -> None:
        planner = FilePlanner(FileConfiguration("graph.jsonl"))

        (step,) = planner.plan(object(), PlanContext())

        self.assertEqual(planner.component_id, "file")
        self.assertEqual(planner.version, "2")
        self.assertEqual(
            planner.runtime_fields,
            (RuntimeField(
                "relative_path",
                "Optional runtime replacement for the relative output path.",
                required=False,
            ),),
        )
        self.assertEqual(step.name, "write")
        self.assertEqual(step.instruction.kind, ("file", "default"))
        self.assertEqual(set(step.instruction.payload), {"relative_path"})
        self.assertEqual(
            step.instruction.payload, {"relative_path": "graph.jsonl"},
        )
        self.assertEqual(
            step.inputs,
            (Input(ArtifactType("core", "graph.*"), None, "records"),),
        )
        self.assertEqual(
            step.outputs,
            (Publication(ArtifactType("file", "write_result"), "result"),),
        )
        self.assertEqual(step.assembly_preference, "deferred")


class MetaGraphPlannerTests(unittest.TestCase):
    def test_the_meta_graph_planner_emits_its_one_deferred_step(self) -> None:
        planner = MetaGraphPlanner(MetaGraphConfiguration())
        model = bound_blueprint(node("Person", "name"))

        (step,) = planner.plan(model, PlanContext())

        self.assertEqual(planner.component_id, "meta_graph")
        self.assertEqual(planner.version, "2")
        self.assertEqual(planner.runtime_fields, ())
        self.assertEqual(step.name, "document")
        self.assertEqual(step.instruction.kind, ("meta_graph", "default"))
        self.assertEqual(
            set(step.instruction.payload),
            {
                "relative_path",
                "example_limit",
                "include_html",
                "html_relative_path",
                "components",
            },
        )
        payload = step.instruction.payload
        assert isinstance(payload, dict)
        self.assertEqual(payload["relative_path"], "meta_graph.json")
        self.assertEqual(payload["components"][0]["name"], "Person")
        self.assertEqual(
            step.inputs,
            (Input(ArtifactType("core", "graph.*"), None, "records"),),
        )
        self.assertEqual(
            step.outputs,
            (
                Publication(
                    ArtifactType("meta_graph", "meta_graph_document"),
                    "result",
                ),
            ),
        )
        self.assertEqual(step.assembly_preference, "deferred")


class Neo4jPlannerTests(unittest.TestCase):
    def test_the_neo4j_planner_emits_one_export_per_component_and_a_script(
        self,
    ) -> None:
        planner = Neo4jPlanner(Neo4jConfiguration())
        model = bound_blueprint(node("Person", "name"))

        export, script = planner.plan(model, PlanContext())

        self.assertEqual(planner.component_id, "neo4j")
        self.assertEqual(planner.version, "2")
        self.assertEqual(
            planner.runtime_fields,
            (RuntimeField(
                "relative_directory",
                "Optional runtime replacement for the Neo4j import-bundle "
                "directory.",
                required=False,
            ),),
        )
        digest = hashlib.sha256(b"Person").hexdigest()[:8]
        self.assertEqual(export.name, f"export.node.Person-{digest}")
        self.assertEqual(export.instruction.kind, ("neo4j", "default"))
        self.assertEqual(
            set(export.instruction.payload),
            {"kind", "component", "relative_directory"},
        )
        export_payload = export.instruction.payload
        assert isinstance(export_payload, dict)
        self.assertEqual(export_payload["kind"], "export_component")
        self.assertEqual(
            set(export_payload["component"]),
            {
                "component",
                "kind",
                "label",
                "relative_path",
                "properties",
                "id_space",
            },
        )
        self.assertEqual(
            export.inputs,
            (
                Input(
                    ArtifactType("core", "graph.node.Person"),
                    None,
                    "records",
                ),
            ),
        )
        self.assertEqual(
            export.outputs,
            (
                Output(
                    ArtifactType("neo4j", "component.node.Person"),
                    "result",
                ),
            ),
        )
        self.assertEqual(export.assembly_preference, "deferred")

        self.assertEqual(script.name, "script")
        self.assertEqual(script.instruction.kind, ("neo4j", "default"))
        self.assertEqual(
            set(script.instruction.payload),
            {
                "kind",
                "components",
                "script_name",
                "default_database",
                "relative_directory",
            },
        )
        script_payload = script.instruction.payload
        assert isinstance(script_payload, dict)
        self.assertEqual(script_payload["kind"], "write_script")
        self.assertEqual(
            script.inputs,
            (
                Input(
                    ArtifactType("neo4j", "component.*"),
                    None,
                    "components",
                ),
            ),
        )
        self.assertEqual(
            script.outputs,
            (
                Publication(
                    ArtifactType("neo4j", "import_bundle"),
                    "result",
                ),
            ),
        )
        self.assertEqual(script.assembly_preference, "deferred")


if __name__ == "__main__":
    unittest.main()
