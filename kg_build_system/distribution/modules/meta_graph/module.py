"""The meta-graph description module."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from ....kernel import ExecutorFactoryContext
from ...internal.adapters.kernel_module import KernelModule
from ...internal.service.paths import validate_relative_path
from ...public.model.registration import ModuleRegistrationConfiguration


@dataclass(frozen=True)
class MetaGraphModuleConfiguration(ModuleRegistrationConfiguration):
    """Where the document lands, and how much of the data it may quote.

    ``example_limit`` bounds the example values quoted per property;
    ``include_html`` also writes a self-contained page at
    ``html_relative_path``. Both paths stay beneath the build output directory.

    Example:
        ```python
        from kg_build_system.distribution import (
            MetaGraphModule, MetaGraphModuleConfiguration, register_module,
        )

        modules = (
            register_module(
                MetaGraphModule,
                MetaGraphModuleConfiguration(example_limit=5),
            ),
        )
        ```
    """

    relative_path: str = "meta_graph.json"
    example_limit: int = 3
    include_html: bool = True
    html_relative_path: str = "meta_graph.html"

    def __post_init__(self) -> None:
        validate_relative_path(
            self.relative_path, context="meta-graph document path",
        )
        validate_relative_path(
            self.html_relative_path, context="meta-graph HTML path",
        )
        if self.example_limit < 0:
            raise ValueError("meta-graph example limit may not be negative")


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
        from .compiler import MetaGraphCompiler

        return MetaGraphCompiler(configuration)

    @classmethod
    def executor(cls, context: ExecutorFactoryContext) -> Any:
        """Create the executor for this module version."""
        from .executor import MetaGraphExecutor

        return MetaGraphExecutor()


__all__ = ["MetaGraphModule", "MetaGraphModuleConfiguration"]
