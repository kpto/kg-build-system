from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from kg_build_system.kernel import (
    Artifact,
    ArtifactType,
    Extension,
    Instruction,
    Layer,
    PlanContext,
    Publication,
    RuntimeField,
    SourceFragment,
    Step,
    StepOutcome,
    StepStatus,
    Toolchain,
    WorkflowRuntime,
)

TEXT = ArtifactType("echo", "text")


@dataclass(frozen=True)
class EchoMessage:
    text: str


class Namespace:
    def __init__(self, *values: object) -> None:
        self._values = values

    def values(self):
        return self._values


class EchoLanguage:
    name = "echo"
    requires: tuple[str, ...] = ()

    def collect(self, namespace):
        return namespace.values()

    def transcribe(self, declarations, context):
        return Layer(
            self.name,
            EchoMessage(" ".join(str(item) for item in declarations)),
        )

    def validate(self, layer):
        assert layer.language == self.name
        assert isinstance(layer.value, EchoMessage)

    def render(self, layer, context):
        return SourceFragment("inline", repr(layer.value.text))


class EchoLinker:
    requires: tuple[str, ...] = ("echo",)

    def link(self, layers):
        value = layers["echo"].value
        assert isinstance(value, EchoMessage)
        return value


class EchoPlanner:
    component_id = "echo"
    version = "1"
    runtime_fields: tuple[RuntimeField, ...] = ()

    def plan(self, model, context: PlanContext):
        assert isinstance(model, EchoMessage)
        return (
            Step(
                component=self.component_id,
                name="echo",
                inputs=(),
                outputs=(Publication(TEXT, "value"),),
                instruction=Instruction(
                    ("echo", "default"), {"text": model.text},
                ),
            ),
        )


class EchoExecutor:
    kinds = (("echo", "default"),)

    def execute(self, context, instruction):
        payload = instruction.payload
        assert isinstance(payload, dict)
        return StepOutcome(
            step_id=context.step_id,
            status=StepStatus.SUCCEEDED,
            artifacts=(Artifact("value", TEXT, payload["text"]),),
        )


class EchoResources:
    def services(self, plan, configuration):
        return None

    def close(self, services):
        return None


class ExtensionBundleTests(unittest.TestCase):
    def test_one_extension_builds_compiles_and_executes(self) -> None:
        extension = Extension(
            "echo",
            languages=(EchoLanguage(),),
            planners=(EchoPlanner(),),
            executors=(EchoExecutor(),),
        )
        toolchain: Toolchain[EchoMessage] = Toolchain(
            languages=extension.languages,
            linker=EchoLinker(),
            planners=extension.planners,
            executors=extension.executors,
            resources=EchoResources(),
            runtime=WorkflowRuntime(),
        )

        model = toolchain.build(Namespace("hello", "world"))
        plan = toolchain.compile(model)
        self.assertEqual(
            [step.instruction.kind for step in plan.steps],
            [("echo", "default")],
        )

        with tempfile.TemporaryDirectory() as directory:
            report = toolchain.execute(plan, output_directory=Path(directory))

        self.assertTrue(report.succeeded)
        self.assertEqual(len(report.published_artifacts), 1)
        published = report.published_artifacts[0]
        self.assertEqual(published.type, TEXT)
        self.assertEqual(published.value, "hello world")


if __name__ == "__main__":
    unittest.main()
