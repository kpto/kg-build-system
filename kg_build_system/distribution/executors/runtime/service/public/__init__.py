"""Author-facing runtime helpers for distribution executors.

The implementations live in the package's private zone; each function here is a
thin delegation kept on the public service path.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kg_build_system.kernel import (
    DisruptedExecutionContext,
    ExecutionContext,
    Instruction,
    StepOutcome,
    StepStatus,
)

from ..internal import (
    DEFAULT_OUTPUT_NAME,
    LocalTemporaryStorage,
    LocalWorkingStorage,
    MappingCredentialResolver,
)


def execution_services(context: Any) -> Any:
    """The services an executor was given, or a clear error when absent.

    Example:
        ```python
        services = execution_services(context)
        ```
    """
    from .._private.outcome import execution_services as implementation

    return implementation(context)


def output_name(given: Any) -> str:
    """The name an output or publication takes in an outcome.

    Example:
        ```python
        name = output_name(Publication(ArtifactType("echo", "text"), "value"))
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
    "DEFAULT_OUTPUT_NAME",
    "LocalTemporaryStorage",
    "LocalWorkingStorage",
    "MappingCredentialResolver",
    "execution_services",
    "instruction_payload",
    "output_name",
    "skipped",
    "succeeded",
]
