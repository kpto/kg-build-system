"""Toolchain flow interface: thin wrappers over the private flow helpers.

The implementation lives in ``service._private``; these functions delegate with
function-local imports so importing this module does not load a private engine.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ...model.public.runtime import RuntimeConfiguration
from ...model.public.workflow import WorkflowPlan


def build_model(
    languages: Sequence[Any], linker: Any, namespace: Any,
) -> Any:
    """Order and transcribe languages, then link their layers."""
    from .._private.pipeline import build_model as implementation

    return implementation(languages, linker, namespace)


def compile_model(
    planners: Sequence[Any], model: Any, context: Any,
) -> WorkflowPlan:
    """Plan every component and assemble the workflow plan."""
    from .._private.pipeline import compile_model as implementation

    return implementation(planners, model, context)


def execute_plan(
    executors: Sequence[Any],
    resources: Any,
    runtime: Any,
    plan: WorkflowPlan,
    *,
    output_directory: Path,
    configuration: RuntimeConfiguration | None = None,
    monitor: Any = None,
) -> Any:
    """Resolve instruction kinds, create services and run one plan."""
    from .._private.pipeline import execute_plan as implementation

    return implementation(
        executors,
        resources,
        runtime,
        plan,
        output_directory=output_directory,
        configuration=configuration,
        monitor=monitor,
    )


def transcribe_layers(
    languages: Sequence[Any],
    namespace: Any,
    declarations: Mapping[str, Sequence[object]] | None = None,
) -> tuple[Any, ...]:
    """Collect, transcribe and validate one layer per language."""
    from .._private.pipeline import transcribe_layers as implementation

    return implementation(languages, namespace, declarations)


__all__ = [
    "build_model", "compile_model", "execute_plan", "transcribe_layers",
]
