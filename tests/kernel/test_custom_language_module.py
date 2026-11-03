from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from kg_build_system.declaration.blueprint import GraphBlueprint
from kg_build_system.declaration.languages.table.model.internal import DataPartDTO
from kg_build_system.declaration.languages.topology.model.internal import GraphPartDTO
from kg_build_system.distribution import (
    ModuleRegistrationConfiguration,
    register_module,
)
from kg_build_system.kernel import (
    Artifact,
    ArtifactType,
    Registry,
    SourceFragment,
    StepOutcome,
    StepStatus,
)
from kg_build_system.pipeline.execution import execute
from kg_build_system.pipeline.compile import compile_blueprint
from kg_build_system.pipeline.contract import (
    ArtifactTypeDTO,
    ContributionDTO,
    InstructionDTO,
    ModuleDefinitionDTO,
    ModuleReferenceDTO,
    PublicationDTO,
    StepDTO,
)


@dataclass(frozen=True)
class EchoMessage:
    text: str


class EchoLanguage:
    name = "echo"
    requires = ()

    def collect(self, namespace):
        return tuple(namespace.values())

    def transcribe(self, declarations, context):
        return EchoMessage(" ".join(str(item) for item in declarations))

    def validate(self, dto):
        assert isinstance(dto, EchoMessage)

    def render(self, dto, context):
        return SourceFragment("inline", repr(dto.text))


@dataclass(frozen=True)
class EchoConfiguration(ModuleRegistrationConfiguration):
    text: str = ""


class EchoCompiler:
    def __init__(self, configuration: EchoConfiguration) -> None:
        self.configuration = configuration

    async def compile(self, context) -> ContributionDTO:
        definition = ModuleDefinitionDTO(
            reference=ModuleReferenceDTO(
                module_id=EchoModule.ID,
                import_module=EchoModule.__module__,
                class_qualname=EchoModule.__qualname__,
                implementation_version=EchoModule.VERSION,
                configuration={"text": self.configuration.text},
            ),
        )
        return ContributionDTO(
            definition,
            (
                StepDTO(
                    name="echo",
                    inputs=(),
                    outputs=(
                        PublicationDTO(ArtifactTypeDTO("echo", "text"), "value"),
                    ),
                    instruction=InstructionDTO("module", None),
                ),
            ),
        )


class EchoExecutor:
    def handle(self, context):
        output = context.step.outputs[0]
        configuration = context.module.reference.configuration or {}
        return StepOutcome(
            context.step_id,
            context.module_id,
            StepStatus.SUCCEEDED,
            (
                Artifact(
                    "value",
                    ArtifactType(output.type.namespace, output.type.name),
                    configuration.get("text", ""),
                ),
            ),
        )

    def handle_disrupted(self, context):
        return StepOutcome(
            context.step_id,
            context.module_id,
            StepStatus.SKIPPED,
        )


class EchoModule:
    ID = "echo"
    VERSION = "1"
    CONFIGURATION_TYPE = EchoConfiguration

    @classmethod
    def compiler(cls, configuration: Any) -> Any:
        return EchoCompiler(configuration)

    @classmethod
    async def create_compiler(cls, context: Any) -> Any:
        return EchoCompiler(context.configuration)

    @classmethod
    def create_executor(cls, context: Any) -> Any:
        return EchoExecutor()


class Namespace:
    def __init__(self, *values: object) -> None:
        self._values = values

    def values(self):
        return self._values


def _empty_blueprint() -> GraphBlueprint:
    return GraphBlueprint(
        graph=GraphPartDTO(),
        data=DataPartDTO(
            structs=(),
            relations=(),
            projections=(),
            sources=(),
        ),
        bindings=(),
        sources=(),
    )


class CustomLanguageModuleTests(unittest.TestCase):
    def test_a_custom_language_transcribes_without_the_defaults(self) -> None:
        build = Registry((EchoLanguage(),)).build(Namespace("hello", "world"))

        self.assertEqual(build.part("echo"), EchoMessage("hello world"))

    def test_a_custom_module_compiles_and_builds_without_the_distribution(self) -> None:
        contract = compile_blueprint(
            _empty_blueprint(),
            modules=(register_module(cast(Any, EchoModule), EchoConfiguration("hello")),),
        )
        self.assertEqual(
            [item.module.reference.module_id for item in contract.contributions],
            ["echo"],
        )
        self.assertEqual(contract.contributions[0].steps[0].name, "echo")

        with tempfile.TemporaryDirectory() as directory:
            report = execute(contract, output_directory=Path(directory), monitor=False)

        self.assertTrue(
            report.succeeded,
            [failure.message for failure in report.unresolved_failures],
        )
        self.assertEqual(report.published_artifacts[0].value, "hello")


if __name__ == "__main__":
    unittest.main()
