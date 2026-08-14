"""Workflow execution API.

The facade is lazy so importing compilation-only workflow IRs does not
initialize the runtime executor or recreate a compile/workflow cycle.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .executor import build
    from .interfaces import CompilationContext
    from .models import (
        BuildRuntime, ContinuableInput, DisruptedExecutionContext, DisruptingInput,
        ExecutionContext, ExecutorFactoryContext, Failure, PublishedArtifact,
        StepOutcome, StepStatus, WorkflowArtifactRoles, WorkflowReport,
    )

_MODEL_EXPORTS = {
    "BuildRuntime", "ContinuableInput", "DisruptedExecutionContext",
    "DisruptingInput", "ExecutionContext", "ExecutorFactoryContext", "Failure",
    "PublishedArtifact", "StepOutcome", "StepStatus", "WorkflowArtifactRoles",
    "WorkflowReport",
}


def __getattr__(name: str) -> Any:
    if name == "build":
        from .executor import build

        return build
    if name == "CompilationContext":
        from .interfaces import CompilationContext

        return CompilationContext
    if name in _MODEL_EXPORTS:
        from . import models

        return getattr(models, name)
    raise AttributeError(name)


__all__ = [
    "BuildRuntime", "CompilationContext", "ContinuableInput",
    "DisruptedExecutionContext", "DisruptingInput", "ExecutionContext",
    "ExecutorFactoryContext", "Failure", "PublishedArtifact", "StepOutcome",
    "StepStatus", "WorkflowArtifactRoles", "WorkflowReport", "build",
]
