"""The hello-world input adapter supplies one relation with one row."""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from pathlib import Path

from kg_build_system.distribution import DuckDbResourceProvider
from kg_build_system.distribution.modules.duckdb import DuckDbService
from kg_build_system.distribution.modules.runtime import skipped, succeeded
from kg_build_system.kernel import (
    ArtifactPattern,
    ArtifactType,
    DisruptedExecutionContext,
    ExecutionContext,
    Input,
    Instruction,
    InstructionKind,
    Language,
    Namespace,
    PlanContext,
    Publication,
    Step,
    StepOutcome,
    Toolchain,
    WorkflowRuntime,
)

from project.modules.hello_world import (
    HELLO_WORLD_RELATION,
    HelloWorldExecutor,
    HelloWorldPlanner,
)

ROW_CHECK = InstructionKind("check", "hello_world")
ROW = ArtifactType.of("hello", "row")


class NullLinker:
    """The adapter test compiles a plan, so the linker is not used."""

    def link(self, languages: Sequence[Language], namespace: Namespace) -> object:
        del languages, namespace
        return object()


class RowCheckPlanner:
    """A test-only consumer: read the adapter's relation at the next step."""

    component_id = "check"
    version = "1"
    runtime_fields = ()

    def plan(self, model: object, context: PlanContext) -> Sequence[Step]:
        del model, context
        return (
            Step(
                component=self.component_id,
                name="row",
                inputs=(
                    Input(
                        ArtifactPattern.of(
                            "core", "data", "table", HELLO_WORLD_RELATION,
                        ),
                        None,
                        "rows",
                    ),
                ),
                outputs=(Publication(ROW),),
                instruction=Instruction(ROW_CHECK, {}),
            ),
        )


class RowCheckExecutor:
    """Query the live relation the adapter registered."""

    kinds = (ROW_CHECK,)
    resources = (DuckDbService,)

    def __init__(self) -> None:
        self.row: tuple[object, ...] | None = None

    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        del instruction
        if isinstance(context, DisruptedExecutionContext):
            return skipped(context)
        contribution = context.inputs["rows"][0]
        assert contribution.artifact is not None
        relations = context.resources.get(DuckDbService).relations
        relation = relations.reference(contribution.artifact.value)
        self.row = relations.query(f"SELECT message FROM {relation}").fetchone()
        return succeeded(context, self.row)


def _toolchain(check: RowCheckExecutor) -> Toolchain[object]:
    return Toolchain(
        languages=(),
        linker=NullLinker(),
        runtime=WorkflowRuntime(providers=(DuckDbResourceProvider(),)),
        planners=(HelloWorldPlanner(), RowCheckPlanner()),
        executors=(HelloWorldExecutor(), check),
    )


def test_the_adapter_is_one_no_input_step() -> None:
    plan = _toolchain(RowCheckExecutor()).compile(object())

    assert plan.steps[0].name == "source.hello_world"
    assert plan.steps[0].inputs == ()
    assert [
        output.type.key.segments for output in plan.steps[0].outputs
    ] == [("core", "data", "table", "hello_world")]
    assert len(plan.connections) == 1


def test_the_adapter_supplies_one_hello_world_row() -> None:
    check = RowCheckExecutor()
    toolchain = _toolchain(check)
    plan = toolchain.compile(object())

    with tempfile.TemporaryDirectory() as directory:
        report = toolchain.execute(plan, output_directory=Path(directory))

    assert check.row == ("hello world",)
    values = {
        artifact.type.key.segments: artifact.value
        for artifact in report.published_artifacts
    }
    assert values[("hello", "row")] == ("hello world",)
