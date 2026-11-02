from __future__ import annotations

import unittest
from dataclasses import dataclass

from kg_build_system._frozen_json import freeze_json, thaw_json
from kg_build_system.compile import compile_build, create_build
from kg_build_system.kernel import (
    Artifact, ArtifactType, ModuleDefinition, ModuleReference, Publication,
    StepOutcome, StepStatus, WorkflowStep, WorkflowContribution,
)
from kg_build_system.modules.internal import (
    ModuleRegistrationConfiguration, register_module,
)


@dataclass(frozen=True)
class EchoIR:
    text: str


class EchoLanguage:
    name = "echo"
    requires = ()

    def __init__(self) -> None:
        self._values: tuple[object, ...] = ()

    def collect(self, namespace):
        self._values = tuple(namespace.values())
        return self._values

    def lower(self, declarations, context):
        return EchoIR(" ".join(str(item) for item in declarations))

    def validate(self, ir):
        assert isinstance(ir, EchoIR)

    def encode(self, ir):
        return {"text": ir.text}

    def decode(self, value):
        return EchoIR(value["text"])


class EchoConfiguration(ModuleRegistrationConfiguration):
    text: str = ""


class EchoCompiler:
    async def compile(self, context):
        definition = ModuleDefinition(ModuleReference(
            "echo", EchoModule.__module__, EchoModule.__qualname__, EchoModule.VERSION, None,
        ))
        return WorkflowContribution(
            definition,
            (WorkflowStep(
                outputs=(Publication(ArtifactType("echo", "text"), "value"),),
                name="echo",
            ),),
            freeze_json({"text": context.build.part("echo").text}),
        )


class EchoExecutor:
    def handle(self, context):
        output = context.step.outputs[0]
        return StepOutcome(
            context.step_id, context.module_id, StepStatus.SUCCEEDED,
            (Artifact("value", output.type, thaw_json(context.variables)["text"]),),
        )

    def handle_disrupted(self, context):
        return StepOutcome(
            context.step_id, context.module_id, StepStatus.SKIPPED,
        )


class EchoModule:
    ID = "echo"
    VERSION = "1"
    CONFIGURATION_TYPE = EchoConfiguration

    @classmethod
    async def create_compiler(cls, context):
        return EchoCompiler()

    @classmethod
    def create_executor(cls, context):
        return EchoExecutor()


class Namespace:
    def __init__(self, *values: object) -> None:
        self._values = values

    def values(self):
        return self._values


class CustomLanguageModuleTests(unittest.TestCase):
    def test_a_custom_language_and_module_compile_without_the_defaults(self) -> None:
        build = create_build(
            languages=(EchoLanguage(),), namespace=Namespace("hello", "world"),
        )
        self.assertEqual(build.part("echo"), EchoIR("hello world"))
        contract = compile_build(
            build=build,
            modules=(register_module(EchoModule, EchoConfiguration()),),
        )
        self.assertEqual(
            [item.reference.module_id for item in contract.workflow.contributions],
            ["echo"],
        )
        self.assertEqual(
            contract.workflow.contributions[0].steps[0].name, "echo",
        )
        from kg_build_system import build
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            report = build(contract, output_directory=Path(directory))
        self.assertTrue(report.succeeded, [f.message for f in report.unresolved_failures])
        self.assertEqual(
            report.published_artifacts[0].value, "hello world",
        )


if __name__ == "__main__":
    unittest.main()
