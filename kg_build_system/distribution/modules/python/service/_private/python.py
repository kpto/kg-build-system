"""Execute a ``python`` step instruction by importing its stable reference."""
from __future__ import annotations

import importlib
from inspect import signature
from typing import Any

from kg_build_system.kernel import (
    DisruptedExecutionContext,
    ExecutionContext,
    Instruction,
    InstructionKind,
    StepOutcome,
)

from ....runtime import instruction_payload, skipped, succeeded


def _load(module_name: str, qualname: str) -> Any:
    value: Any = importlib.import_module(module_name)
    for part in qualname.split("."):
        value = getattr(value, part)
    return value


def _invoke(
    target: Any,
    context: ExecutionContext,
    instruction: Instruction,
) -> Any:
    execute = getattr(target, "execute", None)
    if callable(execute):
        return execute(context, instruction)
    if not callable(target):
        raise TypeError("a python instruction target must be callable")
    try:
        bound = signature(target)
    except (TypeError, ValueError):
        return target(context)
    try:
        bound.bind(context, instruction)
    except TypeError:
        bound.bind(context)
        return target(context)
    return target(context, instruction)


class PythonExecutor:
    """Import ``payload.module``/``payload.qualname`` and execute the target."""

    kinds: tuple[InstructionKind, ...] = (InstructionKind("python", "cpython"),)
    resources: tuple[type, ...] = ()

    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        """Run the imported target and turn its result into a step outcome.

        Example:
            ```python
            outcome = PythonExecutor().execute(context, instruction)
            ```
        """
        if isinstance(context, DisruptedExecutionContext):
            return skipped(context)
        payload = instruction_payload(instruction)
        module_name = payload.get("module")
        qualname = payload.get("qualname")
        if not isinstance(module_name, str) or not module_name:
            raise ValueError(
                "a python instruction requires a non-empty 'module' payload"
            )
        if not isinstance(qualname, str) or not qualname:
            raise ValueError(
                "a python instruction requires a non-empty 'qualname' payload"
            )
        result = _invoke(_load(module_name, qualname), context, instruction)
        if isinstance(result, StepOutcome):
            return result
        return succeeded(context, result)


__all__ = ["PythonExecutor"]
