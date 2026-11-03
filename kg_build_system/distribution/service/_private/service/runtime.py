"""Small runtime adapters shared by the supplied build modules.

The kernel execution context carries a ``services`` value rather than the
individual runtime facilities. These helpers state the shapes a module depends
on in one place: a JSON object payload, the execution services, an output name
and the two ordinary outcomes.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kg_build_system.kernel.model.internal.json import FrozenObject, thaw_json
from .....kernel import Artifact, Given, StepOutcome, StepStatus


def thaw_object(value: Any) -> Any:
    """Return an object payload as plain Python values.

    A value that travelled through the contract is immutable and cares only
    about JSON. A value supplied directly by a compiler or executor factory is
    already plain data. Accept both without making every module restate the
    distinction.
    """
    return thaw_json(value) if isinstance(value, FrozenObject) else value


def as_mapping(value: Any, *, context: str) -> Mapping[str, Any]:
    value = thaw_object(value)
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{context} requires an object payload")
    return value


def instruction_payload(context: Any) -> Any:
    """The instruction one module filed under the running step's name."""
    variables = as_mapping(context.variables, context="module variables")
    instructions = as_mapping(
        variables.get("instructions"), context="module instructions",
    )
    return instructions[context.step.name]


def execution_services(context: Any, services: Any = None) -> Any:
    """The services an executor was given, from its argument or its context.

    The kernel passes services separately; older callers put them on the
    execution context. Both shapes name the same value.
    """
    resolved = services if services is not None else getattr(context, "services", None)
    if resolved is None:
        raise RuntimeError("module executors require execution services")
    return resolved


def output_name(given: Given) -> str:
    """The name an output or publication takes in an outcome."""
    return given.name or "output"


def success(
    context: Any,
    value: Any,
    *,
    status: StepStatus = StepStatus.SUCCEEDED,
) -> StepOutcome:
    """The outcome of a step that emits its one declared output."""
    output = context.step.outputs[0]
    return StepOutcome(
        step_id=context.step_id,
        module_id=context.module_id,
        status=status,
        artifacts=(Artifact(output_name(output), output.type, value),),
    )


def skipped(context: Any) -> StepOutcome:
    """The default disrupted policy: hand the failure on without running."""
    return StepOutcome(
        step_id=context.step_id,
        module_id=context.module_id,
        status=StepStatus.SKIPPED,
    )


__all__ = [
    "as_mapping",
    "execution_services",
    "instruction_payload",
    "output_name",
    "skipped",
    "success",
    "thaw_object",
]
