"""Runtime helpers shared by distribution step executors."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from kg_build_system.kernel import (
    Artifact,
    DisruptedExecutionContext,
    ExecutionContext,
    Instruction,
    StepOutcome,
    StepStatus,
)
from kg_build_system.kernel.model.internal.json import thaw_json

DEFAULT_OUTPUT_NAME = "output"


def output_name(given: Any) -> str:
    """The name an output or publication takes in an outcome."""
    return given.name or DEFAULT_OUTPUT_NAME


def succeeded(
    context: ExecutionContext,
    value: Any,
    *,
    status: StepStatus = StepStatus.SUCCEEDED,
) -> StepOutcome:
    """The outcome of a step that emits its first declared output."""
    artifacts: tuple[Artifact, ...] = ()
    if context.step.outputs:
        output = context.step.outputs[0]
        artifacts = (Artifact(output_name(output), output.type, value),)
    return StepOutcome(
        step_id=context.step_id,
        status=status,
        artifacts=artifacts,
    )


def skipped(context: DisruptedExecutionContext) -> StepOutcome:
    """The default disrupted policy: carry the failure forward without running."""
    return StepOutcome(
        step_id=context.step_id,
        status=StepStatus.SKIPPED,
    )


def instruction_payload(instruction: Instruction) -> Mapping[str, Any]:
    """Return one instruction payload as a plain JSON object."""
    value: Any = thaw_json(cast(Any, instruction.payload))
    if not isinstance(value, Mapping):
        raise TypeError(
            f"instruction kind {instruction.kind!r} requires an object payload"
        )
    return value


__all__ = [
    "DEFAULT_OUTPUT_NAME",
    "instruction_payload",
    "output_name",
    "skipped",
    "succeeded",
]
