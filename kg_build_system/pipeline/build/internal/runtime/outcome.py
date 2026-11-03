"""Outcome values shared by instruction executors."""
from __future__ import annotations

from typing import Any

from .....kernel import (
    Artifact,
    DisruptedExecutionContext,
    ExecutionContext,
    StepOutcome,
    StepStatus,
)
from .identity import output_name


def succeeded(
    context: ExecutionContext,
    value: Any,
    *,
    status: StepStatus = StepStatus.SUCCEEDED,
) -> StepOutcome:
    """The outcome of a step that emits its first declared output."""
    artifacts = ()
    if context.step.outputs:
        output = context.step.outputs[0]
        artifacts = (Artifact(output_name(output), output.type, value),)
    return StepOutcome(
        step_id=context.step_id,
        module_id=context.module_id,
        status=status,
        artifacts=artifacts,
    )


def skipped(context: DisruptedExecutionContext) -> StepOutcome:
    """The default disrupted policy: carry the failure forward without running."""
    return StepOutcome(
        step_id=context.step_id,
        module_id=context.module_id,
        status=StepStatus.SKIPPED,
    )


__all__ = ["skipped", "succeeded"]
