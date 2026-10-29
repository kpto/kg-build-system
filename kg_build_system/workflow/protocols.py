"""Runtime capabilities implemented by executable workflow modules."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Protocol

from .services import ExecutionServices
from .models import (
    DisruptedExecutionContext,
    ExecutionContext,
    ExecutorFactoryContext,
    StepOutcome,
    StepStatus,
)


class ModuleExecutor(ABC):
    """Handles a step according to the state of its connected inputs."""

    @abstractmethod
    def handle(self, context: ExecutionContext, services: ExecutionServices) -> StepOutcome:
        """Handle a step whose every input producer succeeded or warned."""

    @abstractmethod
    def handle_disrupted(self, context: DisruptedExecutionContext, services: ExecutionServices) -> StepOutcome:
        """Default response to failed or skipped inputs: skip this step."""
        return StepOutcome(
            step_id=context.step_id,
            module_id=context.module_id,
            status=StepStatus.SKIPPED,
        )


class ExecutableModule(Protocol):
    ID: ClassVar[str]
    VERSION: ClassVar[str]

    @classmethod
    def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor: ...


__all__ = ["ExecutableModule", "ModuleExecutor"]
