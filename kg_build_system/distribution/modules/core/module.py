"""The core module declaration and its configuration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from ....kernel import ExecutorFactoryContext
from ...internal.adapters.kernel_module import KernelModule
from ...public.model.registration import ModuleRegistrationConfiguration


@dataclass(frozen=True)
class CoreConfiguration(ModuleRegistrationConfiguration):
    """The mandatory core module has no author-configurable behaviour.

    Example:
        ```python
        from kg_build_system.distribution.modules.core import CoreConfiguration

        CoreConfiguration().to_json()
        ```
    """


class CoreModule(KernelModule):
    """Materialise sources, projections, bindings and graph records.

    The composition root appends the core module after the supplied modules; a
    graph author never has to register it by hand. It has no configuration.

    Example:
        ```python
        from kg_build_system.distribution import register_module
        from kg_build_system.distribution.modules.core import CoreModule

        modules = (register_module(CoreModule),)
        ```
    """

    ID: ClassVar[str] = "core"
    VERSION: ClassVar[str] = "3"
    CONFIGURATION_TYPE: ClassVar[type[CoreConfiguration]] = CoreConfiguration

    @classmethod
    def compiler(cls, configuration: Any) -> Any:
        """Create the compiler for this module version."""
        from .compiler import CoreCompiler

        return CoreCompiler()

    @classmethod
    def executor(cls, context: ExecutorFactoryContext) -> Any:
        """Create the executor for this module version."""
        from .executor import CoreExecutor

        return CoreExecutor()


__all__ = ["CoreConfiguration", "CoreModule"]
