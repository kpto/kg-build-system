from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from kg_build_system.kernel import (
    Artifact,
    ArtifactType,
    Component,
    Connection,
    Input,
    Instruction,
    Layer,
    Output,
    Publication,
    RuntimeField,
    SourceFragment,
    Step,
    StepOutcome,
    StepStatus,
    Toolchain,
    WorkflowPlan,
    WorkflowReport,
)
from kg_build_system.kernel.service._private.runtime import WorkflowRuntime
from kg_build_system.kernel.service.internal.workflow_codec import (
    workflow_plan_from_document,
    workflow_plan_to_document,
)

ROOT = Path(__file__).resolve().parents[2]
DEMO = ArtifactType("demo", "value")


class Namespace:
    def __init__(self, *values: object) -> None:
        self._values = values

    def values(self):
        return self._values


class LanguageA:
    name = "a"
    requires: tuple[str, ...] = ()

    def collect(self, namespace):
        return namespace.values()

    def transcribe(self, declarations, context):
        return Layer(self.name, tuple(declarations))

    def validate(self, layer):
        assert layer.language == self.name

    def render(self, layer, context):
        return SourceFragment("inline", repr(layer.value))


class LanguageB:
    name = "b"
    requires: tuple[str, ...] = ("a",)

    def collect(self, namespace):
        return ()

    def transcribe(self, declarations, context):
        return Layer(self.name, (*context.layer("a").value, "b"))

    def validate(self, layer):
        assert layer.language == self.name

    def render(self, layer, context):
        return SourceFragment("inline", repr(layer.value))


class RecordingLinker:
    requires: tuple[str, ...] = ("a", "b")

    def __init__(self) -> None:
        self.layers: dict[str, Layer] | None = None

    def link(self, layers):
        self.layers = dict(layers)
        return tuple(layer.value for layer in layers.values())


class Resources:
    def __init__(self) -> None:
        self.opened = 0
        self.closed: Any = None

    def services(self, plan, configuration):
        self.opened += 1
        return {"plan": plan, "configuration": configuration}

    def close(self, services):
        self.closed = services


class FailingRuntime:
    def execute(self, plan, executors, *, services, configuration, monitor=None):
        raise AssertionError("runtime must not run")


class ProducerPlanner:
    component_id = "producer"
    version = "1"
    runtime_fields: tuple[RuntimeField, ...] = ()

    def plan(self, model, context):
        return (
            Step(
                self.component_id,
                "make",
                (),
                (Publication(DEMO, "value"),),
                Instruction(("test", "default"), None),
            ),
        )


class ConsumerPlanner:
    component_id = "consumer"
    version = "1"
    runtime_fields: tuple[RuntimeField, ...] = ()

    def plan(self, model, context):
        return (
            Step(
                self.component_id,
                "use",
                (Input(DEMO, None, "value"),),
                (Publication(DEMO, "value"),),
                Instruction(("test", "default"), None),
            ),
        )


class DuplicateStepPlanner:
    component_id = "duplicate"
    version = "1"
    runtime_fields: tuple[RuntimeField, ...] = ()

    def plan(self, model, context):
        instruction = Instruction(("test", "default"), None)
        return (
            Step("duplicate", "same", (), (Publication(DEMO, "value"),), instruction),
            Step("duplicate", "same", (), (Publication(DEMO, "other"),), instruction),
        )


class RecordingExecutor:
    kinds: tuple[tuple[str, ...], ...] = (("test", "default"),)

    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(self, context, instruction):
        self.calls.append(context.step_id)
        output = context.step.outputs[0]
        return StepOutcome(
            context.step_id,
            StepStatus.SUCCEEDED,
            (
                Artifact(
                    output.name or "output",
                    output.type,
                    context.step_id,
                ),
            ),
        )


def _plan(instruction: Instruction) -> WorkflowPlan:
    component = Component("producer", "1")
    return WorkflowPlan(
        components=(component,),
        steps=(
            Step(
                "producer",
                "make",
                (),
                (Publication(DEMO, "value"),),
                instruction,
            ),
        ),
    )


class ToolchainFlowTests(unittest.TestCase):
    def test_build_orders_languages_and_links_layers(self) -> None:
        linker = RecordingLinker()
        toolchain = Toolchain(
            languages=(LanguageB(), LanguageA()),
            linker=linker,
            resources=Resources(),
            runtime=WorkflowRuntime(),
        )

        model = toolchain.build(Namespace(1, 2))

        self.assertEqual(model, ((1, 2), (1, 2, "b")))
        self.assertIsNotNone(linker.layers)
        assert linker.layers is not None
        self.assertEqual(linker.layers["a"].value, (1, 2))
        self.assertEqual(linker.layers["b"].value, (1, 2, "b"))

    def test_compile_assigns_components_and_assembles_connections(self) -> None:
        toolchain: Toolchain[Any] = Toolchain(
            languages=(),
            linker=RecordingLinker(),
            resources=Resources(),
            runtime=WorkflowRuntime(),
            planners=(ProducerPlanner(), ConsumerPlanner()),
        )

        plan = toolchain.compile(object())

        self.assertEqual(
            [component.id for component in plan.components],
            ["producer", "consumer"],
        )
        self.assertEqual(
            [step.component for step in plan.steps],
            ["producer", "consumer"],
        )
        self.assertEqual(
            plan.connections,
            (Connection("consumer.use.value", "producer.make.value"),),
        )
        consumer = plan.steps[1]
        self.assertEqual(consumer.inputs[0].name, "value")
        self.assertEqual(consumer.inputs[0].input_name, "value")

    def test_duplicate_step_identity_is_refused(self) -> None:
        toolchain: Toolchain[Any] = Toolchain(
            languages=(),
            linker=RecordingLinker(),
            resources=Resources(),
            runtime=WorkflowRuntime(),
            planners=(DuplicateStepPlanner(),),
        )

        with self.assertRaisesRegex(ValueError, "duplicate step id"):
            toolchain.compile(object())

    def test_unknown_instruction_kind_is_refused_before_execution(self) -> None:
        resources = Resources()
        toolchain = Toolchain(
            languages=(),
            linker=RecordingLinker(),
            resources=resources,
            runtime=FailingRuntime(),
        )

        with self.assertRaisesRegex(ValueError, "no executor"):
            toolchain.execute(
                _plan(Instruction(("missing", "default"), None)),
                output_directory=Path("build"),
            )
        self.assertEqual(resources.opened, 0)

    def test_toolchain_execute_runs_steps_in_dependency_order(self) -> None:
        executor = RecordingExecutor()
        resources = Resources()
        toolchain: Toolchain[Any] = Toolchain(
            languages=(),
            linker=RecordingLinker(),
            resources=resources,
            runtime=WorkflowRuntime(),
            planners=(ProducerPlanner(), ConsumerPlanner()),
            executors=(executor,),
        )
        plan = toolchain.compile(object())

        with tempfile.TemporaryDirectory() as directory:
            report = toolchain.execute(plan, output_directory=Path(directory))

        self.assertIsInstance(report, WorkflowReport)
        self.assertEqual(executor.calls, ["producer.make", "consumer.use"])
        self.assertEqual(
            [artifact.value for artifact in report.published_artifacts],
            ["producer.make", "consumer.use"],
        )
        self.assertIsNotNone(resources.closed)

    def test_workflow_plan_round_trips_through_document(self) -> None:
        component = Component(
            "echo",
            "1",
            (RuntimeField("prefix", "Text to prepend", secret=True),),
        )
        plan = WorkflowPlan(
            components=(component,),
            steps=(
                Step(
                    "echo",
                    "echo",
                    (Input(DEMO, "value", "value"),),
                    (Output(DEMO, "value"), Publication(DEMO, "report")),
                    Instruction(("echo", "default"), {"text": "hello"}),
                    assembly_preference="deferred",
                ),
            ),
            connections=(Connection("echo.echo.value", "echo.echo.value"),),
            provenance={"source": "test", "count": 1},
        )

        document = workflow_plan_to_document(plan)
        encoded = json.dumps(document)
        decoded = workflow_plan_from_document(json.loads(encoded))

        self.assertIsInstance(document["steps"][0]["instruction"]["kind"], list)
        self.assertIsInstance(decoded.steps[0].instruction.kind, tuple)
        self.assertEqual(decoded, plan)

    def test_kernel_imports_no_distribution_or_engine(self) -> None:
        code = (
            "import sys\n"
            "import kg_build_system.kernel\n"
            "removed = 'kg_build_system.' + 'pipeline'\n"
            "for prefix in ('kg_build_system.distribution', removed):\n"
            "    assert not any(\n"
            "        name == prefix or name.startswith(prefix + '.')\n"
            "        for name in sys.modules\n"
            "    ), prefix\n"
            "for name in ('duckdb', 'pyarrow', 'sqlglot'):\n"
            "    assert name not in sys.modules, name\n"
            "print('ok')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "ok")


if __name__ == "__main__":
    unittest.main()
