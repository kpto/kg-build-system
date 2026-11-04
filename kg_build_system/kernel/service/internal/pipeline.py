"""Toolchain flow interface: thin wrappers over the private flow helpers.

The implementation lives in ``service._private``; these functions delegate with
function-local imports so importing this module does not load a private engine.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ...model.public.runtime import RuntimeConfiguration
from ...model.public.workflow import WorkflowPlan


def build_model(
    languages: Sequence[Any], linker: Any, namespace: Any,
) -> Any:
    """Hand the language declarations to the linker."""
    from .._private.pipeline import build_model as implementation

    return implementation(languages, linker, namespace)


def compile_model(
    planners: Sequence[Any], model: Any, context: Any,
) -> WorkflowPlan:
    """Group planners by component and assemble the workflow plan."""
    from .._private.pipeline import compile_model as implementation

    return implementation(planners, model, context)


def execute_plan(
    executors: Sequence[Any],
    runtime: Any,
    plan: WorkflowPlan,
    *,
    output_directory: Path,
    configuration: RuntimeConfiguration | None = None,
    monitor: Any = None,
) -> Any:
    """Resolve instruction kinds and run one plan through the runtime."""
    from .._private.pipeline import execute_plan as implementation

    return implementation(
        executors,
        runtime,
        plan,
        output_directory=output_directory,
        configuration=configuration,
        monitor=monitor,
    )


__all__ = ["build_model", "compile_model", "execute_plan"]
