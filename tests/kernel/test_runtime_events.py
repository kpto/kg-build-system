from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kg_build_system.api import execute as api_execute
from kg_build_system.kernel import (
    Artifact,
    ArtifactType,
    Component,
    Instruction,
    InstructionKind,
    Key,
    PipelineFinished,
    PipelineHalted,
    PipelineStarted,
    Publication,
    RuntimeConfiguration,
    Step,
    StepFinished,
    StepId,
    StepLogged,
    StepOutcome,
    StepStarted,
    StepStatus,
    Toolchain,
    WorkflowPlan,
    WorkflowReport,
    WorkflowRuntime,
)

VALUE = ArtifactType.of("demo", "value")
KIND = InstructionKind("test", "default")


def _plan() -> WorkflowPlan:
    return WorkflowPlan(
        components=(Component("demo", "1"),),
        steps=(
            Step(
                "demo",
                "make",
                (),
                (Publication(VALUE, Key(("value",))),),
                Instruction(KIND, None),
            ),
        ),
    )


def _configuration(**overrides) -> RuntimeConfiguration:
    return RuntimeConfiguration(
        output_directory=Path("build"),
        working_directory=Path("build/_workdir"),
        **overrides,
    )


class _Recording:
    def __init__(self) -> None:
        self.events: list[object] = []

    def on_event(self, event: object) -> None:
        self.events.append(event)

    def kinds(self, event_type: type) -> list[object]:
        return [event for event in self.events if isinstance(event, event_type)]


class _Executor:
    kinds = (KIND,)

    def __init__(self, resources=(), *, log: bool = False) -> None:
        self.resources = resources
        self.log = log
        self.seen: list[StepId] = []

    def execute(self, context, instruction):
        self.seen.append(context.step_id)
        if self.log:
            context.logger.info("rows %s", 3)
        return StepOutcome(
            context.step_id,
            StepStatus.SUCCEEDED,
            (Artifact(Key(("value",)), VALUE, "ok"),),
        )


class _Provider:
    def __init__(self) -> None:
        self.started = False
        self.disposed = False

    def on_event(self, event: object) -> None:
        if isinstance(event, PipelineStarted):
            self.started = True
            event.resources.add(int, 7)
        elif isinstance(event, (PipelineFinished, PipelineHalted)):
            self.disposed = self.started
            self.started = False


class _ListenerFailure(RuntimeError):
    pass


class _ExplodingListener:
    def on_event(self, event: object) -> None:
        if isinstance(event, StepStarted):
            raise _ListenerFailure("listener failed")


class _Linker:
    def link(self, languages, namespace):
        return object()


class RuntimeEventTests(unittest.TestCase):
    def test_runtime_emits_pipeline_events(self) -> None:
        listener = _Recording()

        report = WorkflowRuntime().execute(
            _plan(),
            {KIND: _Executor()},
            configuration=_configuration(),
            listeners=(listener,),
        )

        self.assertTrue(report.succeeded)
        self.assertEqual(
            [type(event) for event in listener.events],
            [
                PipelineStarted,
                StepStarted,
                StepFinished,
                PipelineFinished,
            ],
        )
        self.assertEqual(
            listener.events[1].step_id,
            StepId("demo", "make"),
        )
        self.assertEqual(
            listener.events[2].outcome.status,
            StepStatus.SUCCEEDED,
        )

    def test_halted_event_on_failure(self) -> None:
        listener = _Recording()

        with self.assertRaisesRegex(ValueError, "unknown component"):
            WorkflowRuntime().execute(
                _plan(),
                {KIND: _Executor()},
                configuration=_configuration(
                    component_configuration={"missing": {}},
                ),
                listeners=(listener,),
            )

        self.assertEqual(
            [type(event) for event in listener.events],
            [PipelineStarted, PipelineHalted],
        )
        halted = listener.events[1]
        self.assertIsInstance(halted, PipelineHalted)
        assert isinstance(halted, PipelineHalted)
        self.assertIsInstance(halted.error, ValueError)

    def test_provider_creates_resources_on_start_and_disposes_on_finish(
        self,
    ) -> None:
        provider = _Provider()
        executor = _Executor((int,))

        report = WorkflowRuntime(providers=(provider,)).execute(
            _plan(),
            {KIND: executor},
            configuration=_configuration(),
        )

        self.assertTrue(report.succeeded)
        self.assertTrue(provider.disposed)
        self.assertFalse(provider.started)

    def test_provider_disposes_on_halt(self) -> None:
        provider = _Provider()

        with self.assertRaisesRegex(ValueError, "unknown component"):
            WorkflowRuntime(providers=(provider,)).execute(
                _plan(),
                {KIND: _Executor()},
                configuration=_configuration(
                    component_configuration={"missing": {}},
                ),
            )

        self.assertTrue(provider.disposed)
        self.assertFalse(provider.started)

    def test_listener_does_not_leak_between_runs(self) -> None:
        first = _Recording()
        second = _Recording()
        runtime = WorkflowRuntime()

        runtime.execute(
            _plan(), {KIND: _Executor()},
            configuration=_configuration(), listeners=(first,),
        )
        first_count = len(first.events)
        runtime.execute(
            _plan(), {KIND: _Executor()},
            configuration=_configuration(), listeners=(second,),
        )

        self.assertEqual(len(first.events), first_count)
        self.assertEqual(
            [type(event) for event in second.events],
            [PipelineStarted, StepStarted, StepFinished, PipelineFinished],
        )

    def test_a_listener_error_is_a_pipeline_failure(self) -> None:
        recording = _Recording()

        with self.assertRaisesRegex(_ListenerFailure, "listener failed"):
            WorkflowRuntime().execute(
                _plan(),
                {KIND: _Executor()},
                configuration=_configuration(),
                listeners=(_ExplodingListener(), recording),
            )

        self.assertEqual(
            [type(event) for event in recording.events],
            [PipelineStarted, PipelineHalted],
        )

    def test_step_logger_emits_step_logged(self) -> None:
        listener = _Recording()

        WorkflowRuntime().execute(
            _plan(),
            {KIND: _Executor(log=True)},
            configuration=_configuration(),
            listeners=(listener,),
        )

        logged = listener.kinds(StepLogged)
        self.assertEqual(len(logged), 1)
        event = logged[0]
        self.assertEqual(event.step_id, StepId("demo", "make"))
        self.assertEqual(event.level, "info")
        self.assertEqual(event.message, "rows 3")

    def test_api_monitor_is_a_frontend_listener(self) -> None:
        listener = _Recording()
        executor = _Executor()
        toolchain: Toolchain[object] = Toolchain(
            languages=(),
            linker=_Linker(),
            executors=(executor,),
            runtime=WorkflowRuntime(),
        )

        with tempfile.TemporaryDirectory() as directory:
            report = api_execute(
                _plan(),
                output_directory=Path(directory),
                toolchain=toolchain,
                monitor=listener,
            )

        self.assertTrue(report.succeeded)
        self.assertEqual(
            [type(event) for event in listener.events],
            [PipelineStarted, StepStarted, StepFinished, PipelineFinished],
        )

    def test_api_monitor_false_subscribes_no_listener(self) -> None:
        captured: list[tuple[object, ...]] = []

        class CapturingRuntime:
            def execute(self, plan, executors, *, configuration, listeners=()):
                captured.append(tuple(listeners))
                return WorkflowReport((), (), (), {})

        toolchain: Toolchain[object] = Toolchain(
            languages=(),
            linker=_Linker(),
            executors=(_Executor(),),
            runtime=CapturingRuntime(),
        )

        with tempfile.TemporaryDirectory() as directory:
            api_execute(
                _plan(),
                output_directory=Path(directory),
                toolchain=toolchain,
                monitor=False,
            )

        self.assertEqual(captured, [()])


if __name__ == "__main__":
    unittest.main()
