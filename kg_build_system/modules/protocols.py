"""Module extension protocols: what a build stage must implement.

Module authoring is framework-internal. A module implementation implements
``Module`` and the compiler/executor protocols; a graph author only registers
a supplied module or reads its configuration.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, TypeVar

from ..compile.interfaces import CompilationContext, ModuleCompiler
from ..workflow.interfaces import ExecutorFactoryContext
from ..workflow.interfaces import ModuleExecutor


ConfigT = TypeVar("ConfigT")


@dataclass(frozen=True, slots=True)
class ModuleRegistrationConfiguration:
    """Serializable, non-secret configuration declared for a module."""

    def to_json(self) -> Any:
        """The JSON-compatible form carried in module provenance."""
        from dataclasses import asdict

        return asdict(self)


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


def module_configuration_json(configuration: ModuleRegistrationConfiguration) -> Any:
    """The JSON-compatible form of a registration configuration."""
    from dataclasses import asdict

    return asdict(configuration)


__all__ = [
    "Module",
    "ModuleRegistration",
    "ModuleRegistrationConfiguration",
    "module_configuration_json",
    "register_module",
]
