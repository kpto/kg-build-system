"""Compile-time workflow contributor protocols and drafts."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, ClassVar, Protocol

from ..compile.models import ArtifactRole, CompiledModule, InputSlot, OutputSlot, WorkflowStep


class StepExecutor(Protocol):
    async def execute_step(self, context: Any, step: WorkflowStep) -> Any: ...


class WorkflowModule(Protocol):
    ID: ClassVar[str]

    @classmethod
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


class ModuleContributor(Protocol):
    @property
    def module_class(self) -> type[WorkflowModule]: ...

    async def declare(self, context: Any) -> ModuleDeclarationDraft: ...


def role_is(role: ArtifactRole) -> CandidatePredicate:
    return lambda _input, output: output.artifact_role == role
