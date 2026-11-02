"""Core module protocol adapter.

The module class is the kernel-facing protocol value; the compiler, executor and
plan live in :mod:`kg_build_system.modules._private.core`. The adapter imports
them on first use so registration does not load the implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from ....compile.internal import ModuleCompiler
from ....kernel import CompilationContext, ExecutorFactoryContext
from ..module import Module, ModuleRegistrationConfiguration


@dataclass(frozen=True)
class CoreConfiguration(ModuleRegistrationConfiguration):
    """The mandatory core module has no author-configurable behaviour.

    Example:
        ```python
        from kg_build_system.modules.core import CoreConfiguration

        CoreConfiguration().to_json()
        ```
    """


class CoreModule(Module):
    """Materialise sources, projections, bindings and graph records.

    The composition root appends the core module after the supplied modules; a
    graph author never has to register it by hand. It has no configuration.

    Example:
        ```python
        from kg_build_system.modules import register_module
        from kg_build_system.modules.core import CoreModule

        modules = (register_module(CoreModule),)
        ```
    """

    ID: ClassVar[str] = "core"
    VERSION: ClassVar[str] = "3"
    CONFIGURATION_TYPE: ClassVar[type[CoreConfiguration]] = CoreConfiguration

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler:
        """Create the compiler for this module version.

        Example:
            ```python
            compiler = await MyModule.create_compiler(context)
            ```
        """
        from ..._private.core.compiler import CoreCompiler

        return CoreCompiler()

    @classmethod
    def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> Any:
        """Create the executor for this module version.

        Example:
            ```python
            executor = MyModule.create_executor(context)
            ```
        """
        from ..._private.core.executor import CoreExecutor

        return CoreExecutor()


__all__ = ["CoreConfiguration", "CoreModule"]
