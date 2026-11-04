"""Author-facing runtime helper functions."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kg_build_system.kernel import (
    DisruptedExecutionContext,
    ExecutionContext,
    Instruction,
    Key,
    StepOutcome,
    StepStatus,
)


def output_name(given: Any) -> Key:
    """The output opening name an output or publication takes in an outcome.

    Example:
        ```python
        name = output_name(
            Publication(ArtifactType.of("echo", "text"), Key(("value",))),
        )
        ```
    """
    from .._private.outcome import output_name as implementation

    return implementation(given)


def succeeded(
    context: ExecutionContext,
    value: Any,
    *,
    status: StepStatus = StepStatus.SUCCEEDED,
) -> StepOutcome:
    """The outcome of a step that emits its first declared output.

    Example:
        ```python
        outcome = succeeded(context, "hello")
        ```
    """
    from .._private.outcome import succeeded as implementation

    return implementation(context, value, status=status)


def skipped(context: DisruptedExecutionContext) -> StepOutcome:
    """The default disrupted policy: carry the failure forward without running.

    Example:
        ```python
        outcome = skipped(context)
        ```
    """
    from .._private.outcome import skipped as implementation

    return implementation(context)


def instruction_payload(instruction: Instruction) -> Mapping[str, Any]:
    """Return one instruction payload as a plain JSON object.

    Example:
        ```python
        payload = instruction_payload(instruction)
        ```
    """
    from .._private.outcome import instruction_payload as implementation

    return implementation(instruction)


__all__ = [
    "instruction_payload",
    "output_name",
    "skipped",
    "succeeded",
]
