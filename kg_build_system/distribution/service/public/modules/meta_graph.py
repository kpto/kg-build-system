"""The meta-graph description module class."""
from __future__ import annotations

from typing import Any, ClassVar

from .....kernel import ExecutorFactoryContext
from ....model.public.modules.meta_graph import MetaGraphModuleConfiguration
from ...internal.adapters.kernel_module import KernelModule


class MetaGraphModule(KernelModule):
    """Write the effective-topology document and optional HTML page.

    The document quotes at most ``example_limit`` values per property;
    ``MetaGraphModuleConfiguration`` controls both output paths and the page.

    Example:
        ```python
        from kg_build_system.distribution import (
            MetaGraphModule, MetaGraphModuleConfiguration, register_module,
        )

        modules = (
            register_module(
                MetaGraphModule,
                MetaGraphModuleConfiguration(example_limit=3),
            ),
        )
        ```
    """

    ID: ClassVar[str] = "meta_graph"
    VERSION: ClassVar[str] = "2"
    CONFIGURATION_TYPE: ClassVar[type[MetaGraphModuleConfiguration]] = (
        MetaGraphModuleConfiguration
    )

    @classmethod
    def compiler(cls, configuration: Any) -> Any:
        """Create the compiler for this module version."""
        from ...internal.modules.meta_graph.module import compiler_for

        return compiler_for(configuration, cls)

    @classmethod
    def executor(cls, context: ExecutorFactoryContext) -> Any:
        """Create the executor for this module version."""
        from ...internal.modules.meta_graph.module import executor_for

        return executor_for(cls.VERSION)


__all__ = ["MetaGraphModule"]
