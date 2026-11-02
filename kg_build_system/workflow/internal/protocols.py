"""Workflow extension protocols."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Protocol

from ...kernel import (
    DisruptedExecutionContext, ExecutionContext, ExecutorFactoryContext,
    StepOutcome, StepStatus,
)


class ModuleExecutor(ABC):
    """Handle a step according to the state of its connected inputs."""

    @abstractmethod
    def handle(self, context: ExecutionContext) -> StepOutcome:
        """Handle a step whose inputs all succeeded or warned."""
        ...

    def handle_disrupted(self, context: DisruptedExecutionContext) -> StepOutcome:
        """Handle failed or skipped inputs; skip this step by default."""
        return StepOutcome(
            step_id=context.step_id,
            module_id=context.module_id,
            status=StepStatus.SKIPPED,
        )


class ExecutableModule(Protocol):
    """Runtime capabilities of a module the executor can import."""

    ID: ClassVar[str]
    VERSION: ClassVar[str]

    @classmethod
    def create_executor(cls, context: ExecutorFactoryContext) -> ModuleExecutor:
        """Create the executor for this module version."""
        ...


__all__ = ["ExecutableModule", "ModuleExecutor"]
