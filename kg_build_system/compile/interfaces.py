"""Compile-time capabilities implemented by workflow modules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Protocol, TypeVar

from ..workflow.models import WorkflowContribution
from .models import BuildBlueprint


ConfigT = TypeVar("ConfigT", covariant=True)


@dataclass(frozen=True, slots=True)
class CompilationContext[ConfigT]:
    blueprint: BuildBlueprint
    module_id: str
    configuration: ConfigT


class ModuleCompiler(Protocol):
    async def compile(
        self, context: CompilationContext[Any],
    ) -> WorkflowContribution: ...


class CompilableModule(Protocol):
    ID: ClassVar[str]
    VERSION: ClassVar[str]
    CONFIGURATION_TYPE: ClassVar[type[Any]]

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler: ...


class CompileModuleRegistration(Protocol[ConfigT]):
    @property
    def module_class(self) -> type[CompilableModule]: ...

    @property
    def configuration(self) -> ConfigT: ...


__all__ = [
    "CompilableModule", "CompilationContext", "CompileModuleRegistration",
    "ModuleCompiler",
]
