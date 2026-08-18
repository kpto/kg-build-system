from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from io import StringIO
from typing import Any, ClassVar

from rich.console import Console

from kg_build_system._frozen_json import thaw_json
from kg_build_system.compile.interfaces import CompilationContext, ModuleCompiler
from kg_build_system.modules import Module, ModuleRegistrationConfiguration
from kg_build_system.workflow import BuildRuntime, build
from kg_build_system.workflow.contracts import create_workflow_contract
from kg_build_system.workflow.interfaces import ModuleExecutor
from kg_build_system.workflow.ir import WorkflowContractIR
from kg_build_system.workflow.monitor import RichWorkflowMonitor
from kg_build_system.workflow.models import (
    Artifact, ArtifactRole, CollectionInputSlot, Connection,
    DisruptedExecutionContext, ExecutionContext, ExecutorFactoryContext,
    Failure, ModuleDefinition, ModuleReference, OutputSlot, RuntimeFieldDefinition,
    SingleInputSlot, StepOutcome, StepStatus, WorkflowArtifactRoles,
    WorkflowContribution, WorkflowDefinition, WorkflowReport, WorkflowStep,
)
from kg_build_system.workflow.validation import validate_workflow


@dataclass(frozen=True)
class RecoveryConfiguration(ModuleRegistrationConfiguration):
    pass


class RecoveryModule(Module):
    ID: ClassVar[str] = "test_recovery"
    VERSION: ClassVar[str] = "1"
    CONFIGURATION_TYPE: ClassVar[type[RecoveryConfiguration]] = RecoveryConfiguration

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler:
        return RecoveryCompiler()

    @classmethod
    def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor:
        return RecoveryExecutor()


class RecoveryCompiler:
    async def compile(
        self, context: CompilationContext[Any],
    ) -> WorkflowContribution:
        raise NotImplementedError


class RecoveryExecutor(ModuleExecutor):
    def handle(self, context: ExecutionContext) -> StepOutcome:
        context.services.logger.info("Handling recovery test step")
        if thaw_json(context.step.payload) == {"action": "fail"}:  # type: ignore[arg-type]
            raise RuntimeError("intentional failure")
        return StepOutcome(
            context.step.step_id, context.step.module_id, StepStatus.SUCCEEDED,
        )

    def handle_disrupted(
        self, context: DisruptedExecutionContext,
    ) -> StepOutcome:
        context.services.logger.warning("Recovering disrupted input")
        output = context.step.outputs[0]
        return StepOutcome(
            context.step.step_id,
            context.step.module_id,
            StepStatus.WARNING,
            (Artifact(output.slot_id, output.artifact_role, {"recovered": True}),),
        )


def _module_definition(
    *, version: str = "1",
    runtime_fields: tuple[RuntimeFieldDefinition, ...] = (),
) -> ModuleDefinition:
    return ModuleDefinition(
        reference=ModuleReference(
            module_id=RecoveryModule.ID,
            import_module=RecoveryModule.__module__,
            class_qualname=RecoveryModule.__qualname__,
            implementation_version=version,
        ),
        runtime_fields=runtime_fields,
    )


def _contract(
    *, version: str = "1",
    runtime_fields: tuple[RuntimeFieldDefinition, ...] = (),
) -> WorkflowContractIR:
    private_role = ArtifactRole(namespace="test_recovery", name="failed")
    published_role = WorkflowArtifactRoles.published(
        RecoveryModule.ID, "report",
    )
    failing = WorkflowStep(
        step_id="test_recovery::fail",
        module_id=RecoveryModule.ID,
        outputs=(OutputSlot(slot_id="test_recovery::fail.output", artifact_role=private_role),),
        payload={"action": "fail"},
    )
    recovery_input = SingleInputSlot(slot_id="test_recovery::recover.input")
    recovering = WorkflowStep(
        step_id="test_recovery::recover",
        module_id=RecoveryModule.ID,
        inputs=(recovery_input,),
        outputs=(OutputSlot(slot_id="test_recovery::recover.output", artifact_role=published_role),),
    )
    workflow = WorkflowDefinition(
        modules=(_module_definition(version=version, runtime_fields=runtime_fields),),
        steps=(failing, recovering),
        connections=(Connection(
            input_slot_id=recovery_input.slot_id,
            output_slot_id=failing.outputs[0].slot_id,
        ),),
    )
    return create_workflow_contract(
        workflow,
        provenance={"test": "workflow_adaptation"},
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

    def step_started(self, step: WorkflowStep, detail: str) -> None:
        self.started.append(step.step_id)

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


class WorkflowDefinitionTests(unittest.TestCase):
    def test_rejects_an_unconnected_collection_input(self) -> None:
        module = _module_definition()
        step = WorkflowStep(
            step_id="test_recovery::consumer",
            module_id=RecoveryModule.ID,
            inputs=(CollectionInputSlot(slot_id="test_recovery::consumer.inputs"),),
        )
        workflow = WorkflowDefinition(modules=(module,), steps=(step,))
        with self.assertRaisesRegex(ValueError, "requires at least one connection"):
            validate_workflow(workflow)

    def test_rejects_a_dependency_cycle_before_execution(self) -> None:
        role = ArtifactRole(namespace="test_recovery", name="value")
        first = WorkflowStep(
            step_id="test_recovery::first",
            module_id=RecoveryModule.ID,
            inputs=(SingleInputSlot(slot_id="test_recovery::first.input"),),
            outputs=(OutputSlot(slot_id="test_recovery::first.output", artifact_role=role),),
        )
        second = WorkflowStep(
            step_id="test_recovery::second",
            module_id=RecoveryModule.ID,
            inputs=(SingleInputSlot(slot_id="test_recovery::second.input"),),
            outputs=(OutputSlot(slot_id="test_recovery::second.output", artifact_role=role),),
        )
        workflow = WorkflowDefinition(
            modules=(_module_definition(),),
            steps=(first, second),
            connections=(
                Connection(
                    input_slot_id=first.inputs[0].slot_id,
                    output_slot_id=second.outputs[0].slot_id,
                ),
                Connection(
                    input_slot_id=second.inputs[0].slot_id,
                    output_slot_id=first.outputs[0].slot_id,
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "contains a cycle"):
            validate_workflow(workflow)


class WorkflowRuntimeTests(unittest.TestCase):
    def test_successful_disrupted_handler_recovers_upstream_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = build(_contract(), output_directory=Path(directory))
        self.assertTrue(report.succeeded)
        self.assertEqual(len(report.recovered_failures), 1)
        self.assertEqual(report.unresolved_failures, ())
        self.assertEqual(report.published_artifacts[0].value, {"recovered": True})

    def test_rejects_an_incompatible_runtime_module_version(self) -> None:
        monitor = RecordingMonitor()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "does not match compiled version"):
                build(
                    _contract(version="2"), output_directory=Path(directory),
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
                    _contract(runtime_fields=(runtime_field,)), runtime,
                    output_directory=Path(directory),
                )

    def test_monitor_receives_step_lifecycle_and_module_logs(self) -> None:
        monitor = RecordingMonitor()
        with tempfile.TemporaryDirectory() as directory:
            build(
                _contract(), output_directory=Path(directory), monitor=monitor,
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
        step = WorkflowStep("test_recovery::only", RecoveryModule.ID)
        workflow = WorkflowDefinition(
            modules=(_module_definition(),), steps=(step,),
        )
        monitor.start(workflow)
        monitor.step_started(step, "Processing 0 input slot(s) → 0 output slot(s)")
        monitor.log("INFO", "first message", step_id=step.step_id)
        monitor.log("INFO", "second message", step_id=step.step_id)
        monitor.log("WARNING", "latest message", step_id=step.step_id)
        monitor.step_finished(
            StepOutcome(step.step_id, step.module_id, StepStatus.SUCCEEDED),
            "succeeded; 0 artifact(s)",
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
        self.assertIn("test_recovery::only", rendered)
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
        step = WorkflowStep("test_recovery::health", RecoveryModule.ID)
        workflow = WorkflowDefinition(
            modules=(_module_definition(),), steps=(step,),
        )
        monitor.start(workflow)
        monitor.step_started(step, "Processing")
        failure = Failure(
            "failed", RecoveryModule.ID, step.step_id, "RuntimeError",
        )
        monitor.step_finished(
            StepOutcome(
                step.step_id, step.module_id, StepStatus.FAILED,
                failure=failure,
            ),
            "failed",
        )
        self.assertIsNotNone(monitor._bar_column)
        self.assertEqual(monitor._bar_column.complete_style, "yellow")
        monitor.workflow_finished(WorkflowReport((), (), (failure,), {}))
        self.assertEqual(monitor._bar_column.complete_style, "red")
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
                _contract(), output_directory=Path(directory), monitor=monitor,
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
        steps = tuple(
            WorkflowStep(f"test_recovery::step_{index}", RecoveryModule.ID)
            for index in range(5)
        )
        workflow = WorkflowDefinition(
            modules=(_module_definition(),), steps=steps,
        )
        monitor.start(workflow)
        monitor.step_started(steps[0], "Processing first")
        monitor.step_finished(
            StepOutcome(steps[0].step_id, steps[0].module_id, StepStatus.SUCCEEDED),
            "succeeded",
        )
        monitor.step_started(steps[1], "Processing second")
        monitor.stop()

        rendered = output.getvalue()
        processing_position = rendered.index(steps[1].step_id)
        recent_position = rendered.index(steps[0].step_id)
        self.assertLess(processing_position, recent_position)
        self.assertIn("… 3 more step(s)", rendered)
        self.assertNotIn(steps[2].step_id, rendered)


if __name__ == "__main__":
    unittest.main()
