from __future__ import annotations

import unittest
from pathlib import Path

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
    ResourceView,
    RuntimeConfiguration,
    Step,
    StepOutcome,
    StepStatus,
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


def _configuration() -> RuntimeConfiguration:
    return RuntimeConfiguration(
        output_directory=Path("build"),
        working_directory=Path("build/_workdir"),
    )


class _Provider:
    def __init__(self, name: str, values: dict[type, object], events: list[str]):
        self.name = name
        self.values = values
        self.events = events
        self.started = False

    def on_event(self, event: object) -> None:
        if isinstance(event, PipelineStarted):
            self.events.append(f"{self.name}:start")
            self.started = True
            for resource, value in self.values.items():
                event.resources.add(resource, value)
        elif isinstance(event, (PipelineFinished, PipelineHalted)) and self.started:
            self.events.append(f"{self.name}:dispose")
            self.started = False


class _Executor:
    kinds = (KIND,)

    def __init__(self, resources=(), *, fail: bool = False) -> None:
        self.resources = resources
        self.fail = fail
        self.seen: list[ResourceView] = []

    def execute(self, context, instruction):
        self.seen.append(context.resources)
        if self.fail:
            raise RuntimeError("step failed")
        return StepOutcome(
            context.step_id,
            StepStatus.SUCCEEDED,
            (Artifact(Key(("value",)), VALUE, "ok"),),
        )


class RuntimeResourceTests(unittest.TestCase):
    def test_a_duplicate_resource_type_is_refused(self) -> None:
        events: list[str] = []
        runtime = WorkflowRuntime(providers=(
            _Provider("first", {int: 1}, events),
            _Provider("second", {int: 2}, events),
        ))

        with self.assertRaisesRegex(ValueError, "duplicate resource type"):
            runtime.execute(
                _plan(), {KIND: _Executor()}, configuration=_configuration(),
            )

        self.assertEqual(
            events,
            [
                "first:start", "second:start",
                "first:dispose", "second:dispose",
            ],
        )

    def test_a_missing_declared_resource_is_refused_before_any_step(self) -> None:
        events: list[str] = []
        executor = _Executor((int,))
        runtime = WorkflowRuntime(providers=(_Provider("only", {}, events),))

        with self.assertRaisesRegex(ValueError, "missing resource"):
            runtime.execute(
                _plan(), {KIND: executor}, configuration=_configuration(),
            )

        self.assertEqual(executor.seen, [])
        self.assertEqual(events, ["only:start", "only:dispose"])

    def test_an_executor_receives_only_its_declared_resources(self) -> None:
        events: list[str] = []
        executor = _Executor((int,))
        runtime = WorkflowRuntime(providers=(
            _Provider("values", {int: 7, str: "hidden"}, events),
        ))

        runtime.execute(
            _plan(), {KIND: executor}, configuration=_configuration(),
        )

        view = executor.seen[0]
        self.assertEqual(view.get(int), 7)
        with self.assertRaisesRegex(KeyError, "builtins.str"):
            view.get(str)

    def test_a_failed_step_still_disposes_its_providers(self) -> None:
        events: list[str] = []
        executor = _Executor((int,), fail=True)
        runtime = WorkflowRuntime(providers=(
            _Provider("first", {int: 1}, events),
            _Provider("second", {str: "two"}, events),
        ))

        report = runtime.execute(
            _plan(), {KIND: executor}, configuration=_configuration(),
        )

        self.assertFalse(report.succeeded)
        self.assertEqual(
            events,
            [
                "first:start", "second:start",
                "first:dispose", "second:dispose",
            ],
        )

    def test_a_provider_that_never_saw_start_does_nothing(self) -> None:
        events: list[str] = []
        provider = _Provider("idle", {int: 1}, events)

        provider.on_event(PipelineFinished(WorkflowReport((), (), (), {})))

        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
