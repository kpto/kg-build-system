"""Combined compile-time and runtime interface for public workflow modules."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, TypeVar

from ..compile.interfaces import CompilationContext, ModuleCompiler
from ..workflow.interfaces import ModuleExecutor
from ..workflow.models import ExecutorFactoryContext


ConfigT = TypeVar("ConfigT")


@dataclass(frozen=True, slots=True)
class ModuleRegistrationConfiguration:
    """Serializable, non-secret configuration declared for a module."""


class Module(ABC):
    ID: ClassVar[str]
    VERSION: ClassVar[str]
    CONFIGURATION_TYPE: ClassVar[type[Any]]

    @classmethod
    @abstractmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler: ...

    @classmethod
    @abstractmethod
    def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor: ...


@dataclass(frozen=True, slots=True)
class ModuleRegistration(Generic[ConfigT]):
    module_class: type[Module]
    configuration: ConfigT

    def __post_init__(self) -> None:
        if not isinstance(self.configuration, self.module_class.CONFIGURATION_TYPE):
            raise TypeError(
                f"{self.module_class.__name__} requires "
                f"{self.module_class.CONFIGURATION_TYPE.__name__} configuration"
            )


def register_module(
    module_class: type[Module],
    configuration: ModuleRegistrationConfiguration | None = None,
) -> ModuleRegistration[Any]:
    resolved = configuration or module_class.CONFIGURATION_TYPE()
    return ModuleRegistration(module_class, resolved)


__all__ = [
    "Module", "ModuleRegistration", "ModuleRegistrationConfiguration",
    "register_module",
]
