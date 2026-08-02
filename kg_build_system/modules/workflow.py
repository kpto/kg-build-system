"""Workflow module base classes and compile-time declaration drafts."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, ClassVar

from ..compile.models import ArtifactRole, CompiledModule, InputSlot, OutputSlot, WorkflowStep


class StepExecutor(ABC):
    @abstractmethod
    async def execute_step(self, context: Any, step: WorkflowStep) -> Any: ...


class WorkflowModule(ABC):
    ID: ClassVar[str]

    @classmethod
    @abstractmethod
    async def create_runtime(cls, configuration: Mapping[str, Any]) -> StepExecutor: ...


CandidatePredicate = Callable[[InputSlot, OutputSlot], bool]


@dataclass(frozen=True)
class WorkflowStepDraft:
    definition: WorkflowStep
    candidates: Mapping[str, CandidatePredicate]


@dataclass(frozen=True)
class ModuleDeclarationDraft:
    module: CompiledModule
    steps: tuple[WorkflowStepDraft, ...]


class ModuleContributor(ABC):
    @property
    @abstractmethod
    def module_class(self) -> type[WorkflowModule]: ...

    @abstractmethod
    async def declare(self, context: Any) -> ModuleDeclarationDraft: ...


def role_is(role: ArtifactRole) -> CandidatePredicate:
    return lambda _input, output: output.artifact_role == role
