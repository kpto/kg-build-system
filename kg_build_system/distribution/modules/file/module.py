"""The JSON Lines file target module."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from ....kernel import ExecutorFactoryContext
from ...internal.adapters.kernel_module import KernelModule
from ...internal.service.paths import validate_relative_path
from ...internal.service.runtime import as_mapping
from ...public.model.registration import ModuleRegistrationConfiguration


@dataclass(frozen=True)
class FileModuleConfiguration(ModuleRegistrationConfiguration):
    """Where the graph file is written, beneath the build output directory.

    ``relative_path`` must stay inside the output directory. The runtime field
    ``relative_path`` may replace it for one build.

    Example:
        ```python
        from kg_build_system.distribution import (
            FileModule, FileModuleConfiguration, register_module,
        )

        modules = (
            register_module(
                FileModule, FileModuleConfiguration("graph.jsonl"),
            ),
        )
        ```
    """

    relative_path: str

    def __post_init__(self) -> None:
        validate_relative_path(self.relative_path, context="file output path")


class FileModule(KernelModule):
    """Write graph records as sorted JSON Lines.

    Registers no publication beyond ``file/write_result``; the file is the
    product. ``FileModuleConfiguration`` names its location.

    Example:
        ```python
        from kg_build_system.distribution import (
            FileModule, FileModuleConfiguration, register_module,
        )

        modules = (
            register_module(
                FileModule, FileModuleConfiguration("graph.jsonl"),
            ),
        )
        ```
    """

    ID: ClassVar[str] = "file"
    VERSION: ClassVar[str] = "1"
    CONFIGURATION_TYPE: ClassVar[type[FileModuleConfiguration]] = (
        FileModuleConfiguration
    )

    @classmethod
    def compiler(cls, configuration: Any) -> Any:
        """Create the compiler for this module version."""
        from .compiler import FileCompiler

        return FileCompiler(configuration)

    @classmethod
    def executor(cls, context: ExecutorFactoryContext) -> Any:
        """Create the executor for this module version."""
        from .executor import FileExecutor

        return FileExecutor(as_mapping(
            context.runtime_configuration, context="file runtime configuration",
        ))


__all__ = ["FileModule", "FileModuleConfiguration"]
