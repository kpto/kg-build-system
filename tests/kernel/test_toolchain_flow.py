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
    Declaration,
    Input,
    Instruction,
    Key,
    Output,
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

    def discover_declarations(self, namespace):
        return tuple(Declaration(value) for value in namespace.values())

    def compute_key(self, declaration):
        return Key((str(declaration.value),))

    def get_kind(self, declaration):
        return "value"

    def owns(self, value):
        return isinstance(value, (str, int))

    def get_identity(self, value):
        if not self.owns(value):
            return None
        return SymbolRef(self.name, Key((str(value),)))

    def get_references(self, value, resolver):
        del value, resolver
        return ()

    def transcribe_many(self, declarations, context):
        del context
        symbols = {}
        for declaration in declarations:
            reference = SymbolRef(
                self.name, self.compute_key(declaration),
            )
            symbols[reference] = Symbol(
                reference.key, "value", declaration.value,
            )
        return symbols

    def render(self, symbol, context):
        del context
        return SourceFragment("inline", repr(symbol.value))


class LanguageB(LanguageA):
    name = "b"

    def discover_declarations(self, namespace):
        del namespace
        return ()

    def transcribe_many(self, declarations, context):
        del declarations
        values = tuple(symbol.value for symbol in context.symbols.values())
        reference = SymbolRef(self.name, Key(("b",)))
        return {
            reference: Symbol(reference.key, "value", (*values, "b")),
        }


class RecordingLinker:
    def __init__(self) -> None:
        self.languages = None
        self.namespace = None

    def link(self, languages, namespace):
        self.languages = tuple(languages)
        self.namespace = namespace
        model: dict[SymbolRef, Symbol] = {}
        for language in languages:
            declarations = tuple(
                language.discover_declarations(namespace)
            )
            model.update(
                language.transcribe_many(declarations, SymbolContext(model)),
            )
        return model


class Resources:
    def __init__(self) -> None:
        self.opened = 0
        self.closed = False

    def resources(self, configuration):
        self.opened += 1
        return {}

    def close(self):
        self.closed = True


class FailingRuntime:
    def execute(self, plan, executors, *, configuration, monitor=None):
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


class FirstSharedPlanner:
    component_id = "shared"
    version = "1"
    runtime_fields: tuple[RuntimeField, ...] = ()

    def plan(self, model, context):
        return (
            Step(
                self.component_id,
                "first",
                (),
                (Publication(ArtifactType("demo", "first")),),
                Instruction(("test", "default"), None),
            ),
        )


class SecondSharedPlanner(FirstSharedPlanner):
    def plan(self, model, context):
        return (
            Step(
                self.component_id,
                "second",
                (),
                (Publication(ArtifactType("demo", "second")),),
                Instruction(("test", "default"), None),
            ),
        )


class RecordingExecutor:
    kinds: tuple[tuple[str, ...], ...] = (("test", "default"),)
    resources: tuple[type, ...] = ()

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
    def test_build_orders_languages_and_links_symbols(self) -> None:
        linker = RecordingLinker()
        toolchain = Toolchain(
            languages=(LanguageA(), LanguageB()),
            linker=linker,
            runtime=WorkflowRuntime(),
        )

        model = toolchain.build(Namespace(1, 2))

        self.assertEqual(
            [language.name for language in linker.languages],
            ["a", "b"],
        )
        values = {str(reference): symbol.value for reference, symbol in model.items()}
        self.assertEqual(values["a:1"], 1)
        self.assertEqual(values["a:2"], 2)
        self.assertEqual(values["b:b"], (1, 2, "b"))

    def test_compile_assigns_components_and_assembles_connections(self) -> None:
        toolchain: Toolchain[Any] = Toolchain(
            languages=(),
            linker=RecordingLinker(),
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

    def test_multiple_planners_share_one_component(self) -> None:
        toolchain: Toolchain[Any] = Toolchain(
            languages=(),
            linker=RecordingLinker(),
            runtime=WorkflowRuntime(),
            planners=(FirstSharedPlanner(), SecondSharedPlanner()),
        )

        plan = toolchain.compile(object())

        self.assertEqual(plan.components, (Component("shared", "1"),))
        self.assertEqual(
            [step.name for step in plan.steps],
            ["first", "second"],
        )
        self.assertEqual(
            {step.component for step in plan.steps},
            {"shared"},
        )

    def test_planners_sharing_a_component_must_agree_on_version(self) -> None:
        second = SecondSharedPlanner()
        second.version = "2"
        toolchain: Toolchain[Any] = Toolchain(
            languages=(),
            linker=RecordingLinker(),
            planners=(FirstSharedPlanner(), second),
        )

        with self.assertRaisesRegex(ValueError, "disagree on version"):
            toolchain.compile(object())

    def test_planners_sharing_a_component_must_agree_on_runtime_fields(self) -> None:
        second = SecondSharedPlanner()
        second.runtime_fields = (RuntimeField("prefix", "Text"),)
        toolchain: Toolchain[Any] = Toolchain(
            languages=(),
            linker=RecordingLinker(),
            planners=(FirstSharedPlanner(), second),
        )

        with self.assertRaisesRegex(ValueError, "disagree on runtime_fields"):
            toolchain.compile(object())

    def test_duplicate_step_identity_across_a_component_is_refused(self) -> None:
        class DuplicateAcross(FirstSharedPlanner):
            def plan(self, model, context):
                return (
                    Step(
                        self.component_id,
                        "first",
                        (),
                        (Publication(ArtifactType("demo", "other")),),
                        Instruction(("test", "default"), None),
                    ),
                )

        toolchain: Toolchain[Any] = Toolchain(
            languages=(),
            linker=RecordingLinker(),
            planners=(FirstSharedPlanner(), DuplicateAcross()),
        )

        with self.assertRaisesRegex(ValueError, "duplicate step id"):
            toolchain.compile(object())

    def test_duplicate_step_identity_is_refused(self) -> None:
        toolchain: Toolchain[Any] = Toolchain(
            languages=(),
            linker=RecordingLinker(),
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
            runtime=WorkflowRuntime(providers=(resources,)),
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
        self.assertTrue(resources.closed)

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
