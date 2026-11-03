"""The core module class."""
from __future__ import annotations

from typing import Any, ClassVar

from .....kernel import ExecutorFactoryContext
from ....model.public.modules.core import CoreConfiguration
from ...internal.adapters.kernel_module import KernelModule


class CoreModule(KernelModule):
    """Materialise sources, projections, bindings and graph records.

    The composition root appends the core module after the supplied modules; a
    graph author never has to register it by hand. It has no configuration.

    Example:
        ```python
        from kg_build_system.distribution import CoreModule, register_module

        modules = (register_module(CoreModule),)
        ```
    """

    ID: ClassVar[str] = "core"
    VERSION: ClassVar[str] = "3"
    CONFIGURATION_TYPE: ClassVar[type[CoreConfiguration]] = CoreConfiguration

    @classmethod
    def compiler(cls, configuration: Any) -> Any:
        """Create the compiler for this module version."""
        from ...internal.modules.core import compiler_for

        return compiler_for(cls)

    @classmethod
    def executor(cls, context: ExecutorFactoryContext) -> Any:
        """Create the executor for this module version."""
        from ...internal.modules.core import executor_for

        return executor_for()


__all__ = ["CoreModule"]
