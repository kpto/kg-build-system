"""Contract tests for the typed pipeline identity model."""
from __future__ import annotations

import json
import unittest

from kg_build_system.kernel import (
    Artifact,
    ArtifactPattern,
    ArtifactType,
    Component,
    Connection,
    Failure,
    Input,
    Instruction,
    InstructionKind,
    Key,
    OpeningDirection,
    OpeningId,
    Output,
    Publication,
    PublishedArtifact,
    Step,
    StepId,
    StepOutcome,
    StepStatus,
    WorkflowPlan,
    WorkflowReport,
)
from kg_build_system.kernel.service._private.runtime import schedule
from kg_build_system.kernel.service.internal.report_codec import (
    workflow_report_to_document,
)
from kg_build_system.kernel.service.internal.workflow_codec import (
    workflow_plan_from_document,
    workflow_plan_to_document,
)

TEXT = ArtifactType.of("echo", "text")


class StepIdentityTests(unittest.TestCase):
    def test_a_dotted_step_name_is_one_key_segment(self) -> None:
        step = StepId("core", "projection.defect")
        self.assertEqual(
            step.key, Key(("core", "projection.defect")),
        )
        self.assertEqual(str(step), "core/projection.defect")

    def test_an_input_and_an_output_with_one_name_are_distinct(self) -> None:
        step = StepId("echo", "echo")
        taken = OpeningId(step, OpeningDirection.INPUT, Key(("value",)))
        given = OpeningId(step, OpeningDirection.OUTPUT, "value")

        self.assertNotEqual(taken, given)
        self.assertNotEqual(taken.key, given.key)
        self.assertEqual(
            taken.key.segments, ("echo", "echo", "input", "value"),
        )
        self.assertEqual(
            given.key.segments, ("echo", "echo", "output", "value"),
        )

    def test_an_expanded_opening_needs_no_delimiter_parser(self) -> None:
        opening = OpeningId(
            StepId("file", "write"),
            OpeningDirection.INPUT,
            Key(("records", "core", "graph", "node", "defect")),
        )
        self.assertEqual(
            opening.key.segments,
            ("file", "write", "input", "records", "core", "graph", "node",
             "defect"),
        )

    def test_a_connection_refuses_the_wrong_direction(self) -> None:
        step = StepId("echo", "echo")
        taken = OpeningId(step, OpeningDirection.INPUT, "value")
        given = OpeningId(step, OpeningDirection.OUTPUT, "value")

        with self.assertRaisesRegex(ValueError, "input opening"):
            Connection(input=given, output=given)
        with self.assertRaisesRegex(ValueError, "output opening"):
            Connection(input=taken, output=taken)
        self.assertEqual(Connection(input=taken, output=given).input, taken)

    def test_a_step_id_refuses_a_slash(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not contain"):
            StepId("core", "a/b")


class ArtifactIdentityTests(unittest.TestCase):
    def test_a_concrete_type_round_trips_its_document(self) -> None:
        artifact_type = ArtifactType.of("core", "graph", "node", "site")
        self.assertEqual(
            artifact_type.key.to_document(),
            ["core", "graph", "node", "site"],
        )
        self.assertEqual(
            ArtifactType(Key.from_document(artifact_type.key.to_document())),
            artifact_type,
        )

    def test_a_pattern_matches_exactly_as_the_key_language_says(self) -> None:
        records = ArtifactPattern.of("core", "graph", "**")
        node_site = ArtifactType.of("core", "graph", "node", "site")

        self.assertTrue(records.matches(node_site))
        self.assertFalse(
            ArtifactPattern.of("core", "graph", "*").matches(node_site)
        )
        self.assertTrue(
            ArtifactPattern.of("core", "graph", "*", "*").matches(node_site)
        )

    def test_a_concrete_type_refuses_every_wildcard(self) -> None:
        for name in ("*", "?", "[seq]"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "wildcard"):
                    ArtifactType.of("core", name)
                with self.assertRaisesRegex(ValueError, "wildcard"):
                    ArtifactType.of("core", "graph", name)

    def test_a_pattern_allows_double_star_only_at_the_end(self) -> None:
        with self.assertRaisesRegex(ValueError, "final"):
            ArtifactPattern.of("core", "**", "graph")

    def test_pattern_exact_returns_the_concrete_type(self) -> None:
        self.assertEqual(
            ArtifactPattern.of("echo", "text").exact(),
            ArtifactType.of("echo", "text"),
        )
        with self.assertRaisesRegex(ValueError, "pattern"):
            ArtifactPattern.of("echo", "**").exact()


class InstructionIdentityTests(unittest.TestCase):
    def test_an_instruction_kind_is_exact_and_two_segment(self) -> None:
        kind = InstructionKind("sql", "duckdb")
        self.assertEqual(kind.key, Key(("sql", "duckdb")))
        self.assertNotEqual(kind, InstructionKind("sql", "other"))
        with self.assertRaisesRegex(ValueError, "operation"):
            InstructionKind("", "duckdb")


class PlanValidationTests(unittest.TestCase):
    def _step(
        self,
        name: str,
        *,
        inputs: tuple[Input, ...] = (),
        outputs: tuple[Output | Publication, ...] = (
            Publication(TEXT, Key(("result",))),
        ),
    ) -> Step:
        return Step(
            "echo",
            name,
            inputs,
            outputs,
            Instruction(InstructionKind("echo", "default"), None),
        )

    def _plan(
        self,
        steps: tuple[Step, ...],
        *,
        components: tuple[Component, ...] = (Component("echo", "1"),),
        connections: tuple[Connection, ...] = (),
    ) -> WorkflowPlan:
        return WorkflowPlan(
            components=components,
            steps=steps,
            connections=connections,
        )

    def test_duplicate_step_ids_are_refused(self) -> None:
        plan = self._plan((self._step("echo"), self._step("echo")))

        with self.assertRaisesRegex(ValueError, "duplicate step id"):
            schedule(plan)

    def test_duplicate_component_ids_are_refused(self) -> None:
        plan = self._plan(
            (self._step("echo"),),
            components=(Component("echo", "1"), Component("echo", "2")),
        )

        with self.assertRaisesRegex(ValueError, "component ids must be unique"):
            schedule(plan)

    def test_a_step_component_must_be_declared(self) -> None:
        plan = self._plan((self._step("echo"),), components=())

        with self.assertRaisesRegex(ValueError, "unknown component"):
            schedule(plan)

    def test_an_unresolved_executable_opening_is_refused(self) -> None:
        plan = self._plan((self._step(
            "echo",
            inputs=(Input(ArtifactPattern.of("echo", "text"), None, "value"),),
        ),))

        with self.assertRaisesRegex(ValueError, "unresolved input"):
            schedule(plan)

    def test_an_unknown_connection_endpoint_is_refused(self) -> None:
        producer = self._step("producer")
        consumer = self._step(
            "consumer",
            inputs=(
                Input(
                    ArtifactPattern.of("echo", "text"),
                    Key(("value",)),
                    "value",
                ),
            ),
        )
        unknown = Connection(
            input=OpeningId(
                StepId("echo", "consumer"),
                OpeningDirection.INPUT,
                Key(("other",)),
            ),
            output=OpeningId(
                StepId("echo", "producer"),
                OpeningDirection.OUTPUT,
                Key(("result",)),
            ),
        )

        with self.assertRaisesRegex(ValueError, "connection input"):
            schedule(self._plan((producer, consumer), connections=(unknown,)))

    def test_duplicate_artifact_names_are_refused(self) -> None:
        plan = self._plan((self._step(
            "echo",
            outputs=(
                Output(TEXT, Key(("value",))),
                Publication(TEXT, Key(("value",))),
            ),
        ),))

        with self.assertRaisesRegex(ValueError, "twice"):
            schedule(plan)

    def test_a_valid_plan_reports_typed_openings(self) -> None:
        producer = self._step("producer")
        consumer = self._step(
            "consumer",
            inputs=(
                Input(
                    ArtifactPattern.of("echo", "text"),
                    Key(("value",)),
                    "value",
                ),
            ),
        )
        connection = Connection(
            input=OpeningId(
                StepId("echo", "consumer"),
                OpeningDirection.INPUT,
                Key(("value",)),
            ),
            output=OpeningId(
                StepId("echo", "producer"),
                OpeningDirection.OUTPUT,
                Key(("result",)),
            ),
        )

        scheduled = schedule(self._plan(
            (producer, consumer), connections=(connection,),
        ))

        self.assertEqual(
            scheduled.output_owner[connection.output],
            StepId("echo", "producer"),
        )
        self.assertEqual(
            scheduled.sources(connection.input), (connection.output,),
        )


class CodecIdentityTests(unittest.TestCase):
    def _plan(self) -> WorkflowPlan:
        step = Step(
            "echo",
            "echo",
            (
                Input(
                    ArtifactPattern.of("echo", "text"),
                    Key(("value",)),
                    "value",
                ),
            ),
            (
                Output(TEXT, Key(("value",))),
                Publication(TEXT, Key(("report",))),
            ),
            Instruction(InstructionKind("echo", "default"), {"text": "hi"}),
        )
        return WorkflowPlan(
            components=(Component("echo", "1"),),
            steps=(step,),
            connections=(Connection(
                input=OpeningId(
                    StepId("echo", "echo"),
                    OpeningDirection.INPUT,
                    Key(("value",)),
                ),
                output=OpeningId(
                    StepId("echo", "echo"),
                    OpeningDirection.OUTPUT,
                    Key(("value",)),
                ),
            ),),
        )

    def test_the_plan_codec_uses_arrays_for_every_identity(self) -> None:
        document = workflow_plan_to_document(self._plan())

        self.assertEqual(document["steps"][0]["id"], ["echo", "echo"])
        self.assertEqual(
            document["steps"][0]["inputs"][0]["type"], ["echo", "text"],
        )
        self.assertEqual(
            document["steps"][0]["inputs"][0]["opening_name"], ["value"],
        )
        self.assertEqual(
            document["steps"][0]["outputs"][1]["opening_name"], ["report"],
        )
        self.assertEqual(
            document["connections"][0]["input"],
            ["echo", "echo", "input", "value"],
        )
        self.assertEqual(
            document["steps"][0]["instruction"]["kind"], ["echo", "default"],
        )

    def test_the_plan_codec_round_trips_every_identity_role(self) -> None:
        plan = self._plan()
        decoded = workflow_plan_from_document(
            json.loads(json.dumps(workflow_plan_to_document(plan))),
        )

        self.assertEqual(decoded, plan)
        self.assertIsInstance(decoded.steps[0].instruction.kind, InstructionKind)
        self.assertIsInstance(decoded.steps[0].inputs[0].type, ArtifactPattern)

    def test_a_bad_opening_direction_is_refused(self) -> None:
        document = workflow_plan_to_document(self._plan())
        document["connections"][0]["input"][2] = "sideways"

        with self.assertRaisesRegex(ValueError, "direction"):
            workflow_plan_from_document(document)


class OutcomeIdentityTests(unittest.TestCase):
    def test_an_outcome_and_its_failure_carry_the_same_step_id(self) -> None:
        step = StepId("echo", "echo")
        failure = Failure("boom", step, "RuntimeError")
        outcome = StepOutcome(
            step,
            StepStatus.FAILED,
            (
                Artifact(Key(("value",)), TEXT, "x"),
            ),
            failure,
        )

        self.assertEqual(outcome.step_id, failure.step_id)
        self.assertEqual(
            outcome.opening(outcome.artifacts[0]).step, step,
        )

    def test_the_report_document_uses_key_arrays(self) -> None:
        step = StepId("echo", "echo")
        report = WorkflowReport(
            published_artifacts=(),
            recovered_failures=(),
            unresolved_failures=(Failure("boom", step, "RuntimeError"),),
            provenance={"plan": {"version": 1}},
        )
        document = workflow_report_to_document(report)

        self.assertEqual(
            document["unresolved_failures"][0]["step_id"],
            ["echo", "echo"],
        )

    def test_a_publication_keeps_its_opening(self) -> None:
        step = StepId("neo4j", "script")
        opening = OpeningId(
            step, OpeningDirection.OUTPUT, Key(("result",)),
        )
        report = WorkflowReport(
            published_artifacts=(
                PublishedArtifact(
                    opening, ArtifactType.of("neo4j", "import_bundle"), {},
                ),
            ),
            recovered_failures=(),
            unresolved_failures=(),
            provenance={},
        )
        document = workflow_report_to_document(report)

        self.assertEqual(
            document["published_artifacts"][0]["opening"],
            ["neo4j", "script", "output", "result"],
        )
        self.assertEqual(
            document["published_artifacts"][0]["type"],
            ["neo4j", "import_bundle"],
        )


if __name__ == "__main__":
    unittest.main()
