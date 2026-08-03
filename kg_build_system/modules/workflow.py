"""Workflow module registration, compilation, and execution contracts."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, ClassVar, Protocol, Self

from ..compile.models import ArtifactRole, InputSlot, ModuleDefinition, OutputSlot, WorkflowStep


@dataclass(frozen=True)
class ModuleRegistrationConfiguration(ABC):
    """Serializable, non-secret configuration declared in a blueprint."""


@dataclass(frozen=True)
class ModuleRegistration[T: ModuleRegistrationConfiguration](ABC):
    configuration: T

    @property
    def module_class(self) -> type[Module]:
        return type(self)


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
    async def compile(self, context: Any) -> ModuleCompilationResult: ...


class ModuleExecutor(Protocol):
    async def execute_step(self, context: Any, step: WorkflowStep) -> Any: ...


class Module(ABC):
    ID: ClassVar[str]

    @classmethod
    @abstractmethod
    async def create_compiler(cls, context: Any) -> ModuleCompiler: ...

    @classmethod
    @abstractmethod
    async def create_executor(cls, context: Any) -> ModuleExecutor: ...


# Transitional compatibility for built-in modules still being moved to Module.
class StepExecutor(ABC):
    @abstractmethod
    async def execute_step(self, context: Any, step: WorkflowStep) -> Any: ...


class WorkflowModule(ABC):
    ID: ClassVar[str]

    @classmethod
    @abstractmethod
    async def create_runtime(cls, configuration: Mapping[str, Any]) -> StepExecutor: ...


class ModuleContributor(ABC):
    @property
    @abstractmethod
    def module_class(self) -> type[WorkflowModule]: ...

    @abstractmethod
    async def declare(self, context: Any) -> ModuleCompilationResult: ...


ModuleDeclarationDraft = ModuleCompilationResult


def role_is(role: ArtifactRole) -> CandidatePredicate:
    return lambda _input, output: output.artifact_role == role
