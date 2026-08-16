"""Runtime capabilities implemented by executable workflow modules."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Protocol

from .models import (
    DisruptedExecutionContext, ExecutionContext, ExecutorFactoryContext,
    StepOutcome, StepStatus,
)


class ModuleExecutor(ABC):
    """Handles a step according to the state of its connected inputs."""

    @abstractmethod
    async def handle(self, context: ExecutionContext) -> StepOutcome:
        """Handle a step whose every input producer succeeded or warned."""

    @abstractmethod
    async def handle_disrupted(self, context: DisruptedExecutionContext) -> StepOutcome:
        """Default response to failed or skipped inputs: skip this step."""
        return StepOutcome(
            step_id=context.step.step_id,
            module_id=context.step.module_id,
            status=StepStatus.SKIPPED,
        )


class ExecutableModule(Protocol):
    ID: ClassVar[str]
    VERSION: ClassVar[str]

    @classmethod
    async def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor: ...


__all__ = ["ExecutableModule", "ModuleExecutor"]
