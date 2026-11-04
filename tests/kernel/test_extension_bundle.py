from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from kg_build_system.kernel import (
    Artifact,
    ArtifactType,
    Declaration,
    Instruction,
    InstructionKind,
    Key,
    PlanContext,
    Publication,
    RuntimeField,
    SourceFragment,
    Step,
    StepOutcome,
    StepStatus,
    Symbol,
    SymbolContext,
    SymbolRef,
    Toolchain,
    WorkflowRuntime,
)

TEXT = ArtifactType.of("echo", "text")


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

    def discover_declarations(self, namespace):
        return tuple(Declaration(value) for value in namespace.values())

    def compute_key(self, declaration):
        return Key((str(declaration.value),))

    def get_kind(self, declaration):
        del declaration
        return "echo"

    def owns(self, value):
        return isinstance(value, str)

    def get_identity(self, value):
        if not isinstance(value, str):
            return None
        return SymbolRef(self.name, Key((value,)))

    def get_references(self, value, resolver):
        del value, resolver
        return ()

    def transcribe_many(self, declarations, context):
        del context
        reference = SymbolRef(self.name, Key(("echo",)))
        return {
            reference: Symbol(
                reference.key,
                "echo",
                EchoMessage(" ".join(
                    str(declaration.value) for declaration in declarations
                )),
            ),
        }

    def render(self, symbol, context):
        del context
        return SourceFragment("inline", repr(symbol.value.text))


class EchoLinker:
    def link(self, languages, namespace):
        language = languages[0]
        declarations = tuple(language.discover_declarations(namespace))
        symbols = language.transcribe_many(
            declarations, SymbolContext(),
        )
        (symbol,) = symbols.values()
        value = symbol.value
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
                outputs=(Publication(TEXT, Key(("value",))),),
                instruction=Instruction(
                    InstructionKind("echo", "default"), {"text": model.text},
                ),
            ),
        )


class EchoExecutor:
    kinds = (InstructionKind("echo", "default"),)
    resources: tuple[type, ...] = ()

    def execute(self, context, instruction):
        payload = instruction.payload
        assert isinstance(payload, dict)
        return StepOutcome(
            step_id=context.step_id,
            status=StepStatus.SUCCEEDED,
            artifacts=(Artifact(Key(("value",)), TEXT, payload["text"]),),
        )


class EchoResources:
    def resources(self, configuration):
        return {}

    def close(self):
        return None


class CompositionTests(unittest.TestCase):
    def test_one_extension_builds_compiles_and_executes(self) -> None:
        toolchain: Toolchain[EchoMessage] = Toolchain(
            languages=(EchoLanguage(),),
            linker=EchoLinker(),
            planners=(EchoPlanner(),),
            executors=(EchoExecutor(),),
            runtime=WorkflowRuntime(providers=(EchoResources(),)),
        )

        model = toolchain.build(Namespace("hello", "world"))
        plan = toolchain.compile(model)
        self.assertEqual(
            [step.instruction.kind for step in plan.steps],
            [InstructionKind("echo", "default")],
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
