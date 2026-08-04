"""Workflow-module registration, compilation, and execution interfaces."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar, Protocol

from ..compile.models import ArtifactRole, BuildBlueprint, BuildOverrides, BuildSettings, InputSlot, ModuleDefinition, OutputSlot, WorkflowStep
from .models import ExecutionContext, StepOutcome


@dataclass(frozen=True)
class ModuleRegistrationConfiguration(ABC):
    """Serializable, non-secret configuration declared in a blueprint."""


@dataclass(frozen=True)
class ModuleRegistration[T: ModuleRegistrationConfiguration](ABC):
    configuration: T

    @property
    def module_class(self) -> type[Module]:
        return type(self)


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


class ModuleExecutor(Protocol):
    async def execute_step(self, context: ExecutionContext) -> StepOutcome: ...


class Module(ABC):
    ID: ClassVar[str]

    @classmethod
    @abstractmethod
    async def create_compiler(cls, context: Any) -> ModuleCompiler: ...

    @classmethod
    @abstractmethod
    async def create_executor(cls, context: Any) -> ModuleExecutor: ...


def role_is(role: ArtifactRole) -> CandidatePredicate:
    return lambda _input, output: output.artifact_role == role
