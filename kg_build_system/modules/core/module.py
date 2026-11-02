"""The mandatory core workflow module."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from ...compile.interfaces import ModuleCompiler
from ...kernel import CompilationContext, ExecutorFactoryContext
from ..interfaces import Module, ModuleRegistrationConfiguration
from .executor import CoreExecutor


@dataclass(frozen=True)
class CoreConfiguration(ModuleRegistrationConfiguration):
    """The mandatory core module has no author-configurable behaviour."""


class CoreModule(Module):
    ID: ClassVar[str] = "core"
    VERSION: ClassVar[str] = "3"
    CONFIGURATION_TYPE: ClassVar[type[CoreConfiguration]] = CoreConfiguration

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler:
        from .compiler import CoreCompiler

        return CoreCompiler()

    @classmethod
    def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> CoreExecutor:
        return CoreExecutor()


__all__ = ["CoreConfiguration", "CoreModule"]
