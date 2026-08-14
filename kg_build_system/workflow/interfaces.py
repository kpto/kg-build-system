"""Workflow-module registration, compilation, and execution interfaces."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar, Protocol, cast

from ..compile.blueprint import BuildBlueprint
from ..compile.contracts import BuildOverrides, BuildSettings
from .models import (
    ArtifactRole, DisruptedExecutionContext, ExecutionContext,
    ExecutorFactoryContext, InputSlot, ModuleDefinition, OutputSlot, StepOutcome,
    StepStatus, WorkflowStep,
)


@dataclass(frozen=True)
class ModuleRegistrationConfiguration(ABC):
    """Serializable, non-secret configuration declared in a blueprint."""


@dataclass(frozen=True)
class ModuleRegistration[T: ModuleRegistrationConfiguration](ABC):
    configuration: T

    @property
    def module_class(self) -> type[Module]:
        return cast(type[Module], type(self))


@dataclass(frozen=True)
class CompilationContext[T: ModuleRegistrationConfiguration]:
    """Generic compile-time context for one configured workflow module."""

    blueprint: BuildBlueprint
    settings: BuildSettings
    overrides: BuildOverrides
    module_id: str
    priority: int
    registration_configuration: T


CandidatePredicate = Callable[[InputSlot, OutputSlot], bool]


@dataclass(frozen=True)
class WorkflowStepDraft:
    definition: WorkflowStep
    candidates: dict[str, CandidatePredicate]


@dataclass(frozen=True)
class ModuleCompilationResult:
    module: ModuleDefinition
    steps: tuple[WorkflowStepDraft, ...]


class ModuleCompiler(Protocol):
    async def compile(self, context: CompilationContext[Any]) -> ModuleCompilationResult: ...


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


class Module(ABC):
    ID: ClassVar[str]

    @classmethod
    @abstractmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler: ...

    @classmethod
    @abstractmethod
    async def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor: ...


def role_is(role: ArtifactRole) -> CandidatePredicate:
    return lambda _input, output: output.artifact_role == role
