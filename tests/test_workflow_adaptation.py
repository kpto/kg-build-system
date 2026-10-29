"""The runtime a module author's steps are run with, and the report the build writes."""
from __future__ import annotations

import tempfile
import unittest
from contextlib import chdir
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any, ClassVar

from rich.console import Console

from kg_build_system._frozen_json import freeze_json
from kg_build_system.compile.interfaces import CompilationContext, ModuleCompiler
from kg_build_system.modules.interfaces import Module, ModuleRegistrationConfiguration
from kg_build_system.workflow import BuildRuntime, build
from kg_build_system.workflow.interfaces import assemble_workflow
from kg_build_system.workflow.interfaces import create_workflow_contract
from kg_build_system.workflow.interfaces import output_name, step_identity
from kg_build_system.workflow.interfaces import ModuleExecutor
from kg_build_system.workflow.ir import WorkflowContractIR
from kg_build_system.workflow.interfaces import (
    Artifact, ArtifactType, DisruptedExecutionContext, ExecutionContext,
    ExecutorFactoryContext, Failure, Input, ModuleDefinition, ModuleReference,
    Output, Publication, RuntimeFieldDefinition, StepOutcome, StepStatus,
    WorkflowContribution, WorkflowDefinition, WorkflowReport, WorkflowStep,
)
from kg_build_system.workflow.interfaces import RichWorkflowMonitor

FAILED = ArtifactType("test_recovery", "failed")
REPORT = ArtifactType("test_recovery", "report")

RECORDS = "records"
MADE_ONE = ArtifactType("test_arrival", "made.one")
MADE_TWO = ArtifactType("test_arrival", "made.two")
MADE_ANY = ArtifactType("test_arrival", "made.*")
COUNTED = ArtifactType("test_arrival", "counted")


@dataclass(frozen=True)
class RecoveryConfiguration(ModuleRegistrationConfiguration):
    pass


class RecoveryModule(Module):
    """A module whose first step fails and whose second absorbs the failure."""

    ID: ClassVar[str] = "test_recovery"
    VERSION: ClassVar[str] = "1"
    CONFIGURATION_TYPE: ClassVar[type[RecoveryConfiguration]] = RecoveryConfiguration

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler:
        raise NotImplementedError("these tests contribute their steps directly")

    @classmethod
    def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor:
        return RecoveryExecutor()


class RecoveryExecutor(ModuleExecutor):
    """Told which of its steps to fail by the instruction filed under that step's name."""

    def handle(
        self, context: ExecutionContext, services: ExecutionServices,
    ) -> StepOutcome:
        services.logger.info("Handling recovery test step")
        if context.variables["instructions"][context.step.name] == {"action": "fail"}:
            raise RuntimeError("intentional failure")
        return StepOutcome(context.step_id, context.module_id, StepStatus.SUCCEEDED)

    def handle_disrupted(
        self, context: DisruptedExecutionContext, services: ExecutionServices,
    ) -> StepOutcome:
        services.logger.warning("Recovering disrupted input")
        published = context.step.outputs[0]
        return StepOutcome(
            context.step_id,
            context.module_id,
            StepStatus.WARNING,
            (Artifact(output_name(published), published.type, {"recovered": True}),),
        )


class ArrivalModule(Module):
    """A module whose last step asks for a family of types with one open input."""

    ID: ClassVar[str] = "test_arrival"
    VERSION: ClassVar[str] = "1"
    CONFIGURATION_TYPE: ClassVar[type[ModuleRegistrationConfiguration]] = (
        ModuleRegistrationConfiguration
    )

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler:
        raise NotImplementedError("these tests contribute their steps directly")

    @classmethod
    def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor:
        return ArrivalExecutor()


class ArrivalExecutor(ModuleExecutor):
    def handle(
        self, context: ExecutionContext, services: ExecutionServices,
    ) -> StepOutcome:
        given = context.step.outputs[0]
        if RECORDS in context.inputs:
            value: Any = [
                item.artifact.type.name
                for item in context.inputs[RECORDS]
                if item.artifact is not None
            ]
        else:
            value = given.type.name
        return StepOutcome(
            context.step_id,
            context.module_id,
            StepStatus.SUCCEEDED,
            (Artifact(output_name(given), given.type, value),),
        )

    def handle_disrupted(
        self, context: DisruptedExecutionContext, services: ExecutionServices,
    ) -> StepOutcome:
        return super().handle_disrupted(context, services)


def _module_definition(
    module: type[Module],
    *, version: str = "1",
    runtime_fields: tuple[RuntimeFieldDefinition, ...] = (),
) -> ModuleDefinition:
    return ModuleDefinition(
        reference=ModuleReference(
            module_id=module.ID,
            import_module=module.__module__,
            class_qualname=module.__qualname__,
            implementation_version=version,
        ),
        runtime_fields=runtime_fields,
    )


def _recovery_contribution(
    *, version: str = "1",
    runtime_fields: tuple[RuntimeFieldDefinition, ...] = (),
) -> WorkflowContribution:
    """The failure and the step that reads it, with the instruction that causes it."""
    return WorkflowContribution(
        _module_definition(
            RecoveryModule, version=version, runtime_fields=runtime_fields,
        ),
        (
            WorkflowStep(outputs=(Output(FAILED, "failed"),), name="fail"),
            WorkflowStep(
                inputs=(Input(FAILED, "failed"),),
                outputs=(Publication(REPORT, "report"),),
                name="recover",
            ),
        ),
        freeze_json({
            "instructions": {
                "fail": {"action": "fail"},
                "recover": {"action": "recover"},
            },
        }),
    )


def _recovery_contract(
    *, version: str = "1",
    runtime_fields: tuple[RuntimeFieldDefinition, ...] = (),
) -> WorkflowContractIR:
    return create_workflow_contract(
        assemble_workflow((
            _recovery_contribution(version=version, runtime_fields=runtime_fields),
        )),
        provenance={"test": "workflow_adaptation"},
    )


def _arrival_contract() -> WorkflowContractIR:
    """Two writers of related types and one step that asks for the family they belong to."""
    contribution = WorkflowContribution(
        _module_definition(ArrivalModule),
        (
            WorkflowStep(outputs=(Output(MADE_ONE, "one"),), name="make_one"),
            WorkflowStep(outputs=(Output(MADE_TWO, "two"),), name="make_two"),
            WorkflowStep(
                inputs=(Input(MADE_ANY, RECORDS),),
                outputs=(Publication(COUNTED, "result"),),
                name="count",
            ),
        ),
    )
    return create_workflow_contract(
        assemble_workflow((contribution,)), provenance={"test": "workflow_adaptation"},
    )


def _definition(*steps: WorkflowStep) -> WorkflowDefinition:
    """The workflow a module's steps assemble into, which is what a monitor is shown."""
    return assemble_workflow((
        WorkflowContribution(_module_definition(RecoveryModule), steps),
    ))


def _published_step(name: str) -> WorkflowStep:
    """A step a build can run on its own, since what it publishes needs no reader."""
    return WorkflowStep(
        outputs=(Publication(ArtifactType(RecoveryModule.ID, name), "result"),), name=name,
    )


class RecordingMonitor:
    def __init__(self) -> None:
        self.started: list[str] = []
        self.finished: list[tuple[str, StepStatus]] = []
        self.logs: list[tuple[str, str, str | None]] = []
        self.start_calls = 0
        self.stop_calls = 0
        self.workflow_reports: list[WorkflowReport] = []
        self.halted_messages: list[str] = []

    def start(self, workflow: WorkflowDefinition) -> None:
        self.start_calls += 1

    def step_started(self, step_id: str, detail: str) -> None:
        self.started.append(step_id)

    def step_finished(self, outcome: StepOutcome, detail: str) -> None:
        self.finished.append((outcome.step_id, outcome.status))

    def workflow_finished(self, report: WorkflowReport) -> None:
        self.workflow_reports.append(report)

    def workflow_halted(self, message: str) -> None:
        self.halted_messages.append(message)

    def log(
        self, level: str, message: str, *, step_id: str | None = None,
    ) -> None:
        self.logs.append((level, message, step_id))

    def stop(self) -> None:
        self.stop_calls += 1


class WorkflowRuntimeTests(unittest.TestCase):
    def test_runtime_working_directory_is_derived_from_its_output(self) -> None:
        output = Path("custom-output")
        runtime = BuildRuntime(output_directory=output)

        self.assertEqual(runtime.working_directory, output / "_workdir")

    def test_default_directories_are_explicit_and_relative_to_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as directory, chdir(directory):
            build(_recovery_contract(), monitor=False)

            output = Path(directory) / "build"
            self.assertTrue((output / "workflow_contract.json").is_file())
            self.assertTrue((output / "build_report.json").is_file())
            self.assertTrue((output / "_workdir").is_dir())

    def test_default_working_directory_follows_custom_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "custom-output"
            build(_recovery_contract(), output_directory=output, monitor=False)

            self.assertTrue((output / "_workdir").is_dir())

    def test_successful_disrupted_handler_recovers_upstream_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = build(_recovery_contract(), output_directory=Path(directory))
        self.assertTrue(report.succeeded)
        self.assertEqual(len(report.recovered_failures), 1)
        self.assertEqual(report.unresolved_failures, ())
        self.assertEqual(report.published_artifacts[0].type, REPORT)
        self.assertEqual(report.published_artifacts[0].value, {"recovered": True})

    def test_an_open_input_arrives_under_the_one_name_it_was_given(self) -> None:
        """One key holds what every type the pattern matched produced."""
        with tempfile.TemporaryDirectory() as directory:
            report = build(_arrival_contract(), output_directory=Path(directory))

        self.assertTrue(report.succeeded)
        self.assertEqual(len(report.published_artifacts), 1)
        self.assertEqual(report.published_artifacts[0].type, COUNTED)
        self.assertEqual(
            report.published_artifacts[0].value, ["made.one", "made.two"],
        )

    def test_rejects_an_incompatible_runtime_module_version(self) -> None:
        monitor = RecordingMonitor()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "does not match compiled version"):
                build(
                    _recovery_contract(version="2"), output_directory=Path(directory),
                    monitor=monitor,
                )
        self.assertEqual(len(monitor.halted_messages), 1)
        self.assertEqual(monitor.workflow_reports, [])
        self.assertEqual(monitor.stop_calls, 1)

    def test_validates_runtime_configuration_types(self) -> None:
        runtime_field = RuntimeFieldDefinition(
            key="attempts", description="Number of attempts.",
            value_type="integer",
        )
        runtime = BuildRuntime(module_configuration={
            RecoveryModule.ID: {"attempts": "three"},
        })
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(TypeError, "invalid runtime configuration"):
                build(
                    _recovery_contract(runtime_fields=(runtime_field,)), runtime,
                    output_directory=Path(directory),
                )

    def test_monitor_receives_step_lifecycle_and_module_logs(self) -> None:
        monitor = RecordingMonitor()
        with tempfile.TemporaryDirectory() as directory:
            build(
                _recovery_contract(), output_directory=Path(directory), monitor=monitor,
            )

        self.assertEqual(monitor.start_calls, 1)
        self.assertEqual(monitor.stop_calls, 1)
        self.assertEqual(len(monitor.workflow_reports), 1)
        self.assertEqual(monitor.halted_messages, [])
        self.assertEqual(monitor.started, [
            "test_recovery::fail", "test_recovery::recover",
        ])
        self.assertEqual(monitor.finished, [
            ("test_recovery::fail", StepStatus.FAILED),
            ("test_recovery::recover", StepStatus.WARNING),
        ])
        self.assertTrue(any(
            message == "Handling recovery test step"
            and step_id == "test_recovery::fail"
            for _level, message, step_id in monitor.logs
        ))
        self.assertTrue(any(
            message == "Recovering disrupted input"
            and step_id == "test_recovery::recover"
            for _level, message, step_id in monitor.logs
        ))


class MonitorTests(unittest.TestCase):
    def test_rich_monitor_renders_progress_steps_and_scrolling_logs(self) -> None:
        output = StringIO()
        console = Console(
            file=output, force_terminal=False, color_system=None, width=100,
        )
        monitor = RichWorkflowMonitor(console=console, log_lines=2)
        monitor.set_duckdb_settings(
            storage="disk", compression=False,
            memory_limit="2GiB", threads=3,
        )
        name = "only"
        identity = step_identity(RecoveryModule.ID, name)
        monitor.start(_definition(_published_step(name)))
        monitor.step_started(identity, "Processing 0 input(s) → 1 output(s)")
        monitor.log("INFO", "first message", step_id=identity)
        monitor.log("INFO", "second message", step_id=identity)
        monitor.log("WARNING", "latest message", step_id=identity)
        monitor.step_finished(
            StepOutcome(identity, RecoveryModule.ID, StepStatus.SUCCEEDED),
            "succeeded; 1 artifact(s)",
        )
        monitor.workflow_finished(WorkflowReport((), (), (), {}))
        monitor.stop()

        rendered = output.getvalue()
        self.assertIn("Workflow", rendered)
        self.assertIn("Succeeded 1/1", rendered)
        self.assertIn("DuckDB disk", rendered)
        self.assertIn("compression off", rendered)
        self.assertIn("memory 2GiB", rendered)
        self.assertIn("threads 3", rendered)
        self.assertIn("Steps", rendered)
        self.assertIn(identity, rendered)
        self.assertIn("Logs", rendered)
        self.assertNotIn("first message", rendered)
        self.assertIn("second message", rendered)
        self.assertIn("latest message", rendered)

    def test_rich_monitor_colors_workflow_health_status_and_bar(self) -> None:
        output = StringIO()
        console = Console(
            file=output, force_terminal=False, color_system=None, width=120,
        )
        monitor = RichWorkflowMonitor(console=console)
        name = "health"
        identity = step_identity(RecoveryModule.ID, name)
        monitor.start(_definition(_published_step(name)))
        monitor.step_started(identity, "Processing")
        failure = Failure("failed", RecoveryModule.ID, identity, "RuntimeError")
        monitor.step_finished(
            StepOutcome(identity, RecoveryModule.ID, StepStatus.FAILED, failure=failure),
            "failed",
        )
        bar_column = monitor._bar_column
        if bar_column is None:
            self.fail("a running monitor draws a progress bar to colour")
        self.assertEqual(bar_column.complete_style, "yellow")
        monitor.workflow_finished(WorkflowReport((), (), (failure,), {}))
        self.assertEqual(bar_column.complete_style, "red")
        monitor.stop()

        rendered = output.getvalue()
        self.assertIn("Halted 1/1 steps", rendered)

    def test_build_monitor_shows_effective_default_duckdb_resources(self) -> None:
        output = StringIO()
        console = Console(
            file=output, force_terminal=False, color_system=None, width=160,
        )
        monitor = RichWorkflowMonitor(console=console)
        with tempfile.TemporaryDirectory() as directory:
            build(
                _recovery_contract(), output_directory=Path(directory), monitor=monitor,
            )

        rendered = output.getvalue()
        self.assertNotIn("memory default", rendered)
        self.assertNotIn("threads default", rendered)
        self.assertRegex(rendered, r"memory [0-9.]+ [A-Za-z]+")
        self.assertRegex(rendered, r"threads [1-9][0-9]*")

    def test_rich_monitor_prioritizes_active_and_recent_steps_in_fixed_view(self) -> None:
        output = StringIO()
        console = Console(
            file=output, force_terminal=False, color_system=None, width=100,
        )
        monitor = RichWorkflowMonitor(console=console, step_lines=3)
        names = tuple(f"step_{index}" for index in range(5))
        steps = tuple(_published_step(name) for name in names)
        identities = [step_identity(RecoveryModule.ID, name) for name in names]
        monitor.start(_definition(*steps))
        monitor.step_started(identities[0], "Processing first")
        monitor.step_finished(
            StepOutcome(identities[0], RecoveryModule.ID, StepStatus.SUCCEEDED),
            "succeeded",
        )
        monitor.step_started(identities[1], "Processing second")
        monitor.stop()

        rendered = output.getvalue()
        processing_position = rendered.index(identities[1])
        recent_position = rendered.index(identities[0])
        self.assertLess(processing_position, recent_position)
        self.assertIn("… 3 more step(s)", rendered)
        self.assertNotIn(identities[2], rendered)


if __name__ == "__main__":
    unittest.main()
