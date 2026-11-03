"""The JSON Lines file target module class."""
from __future__ import annotations

from typing import Any, ClassVar

from .....kernel import ExecutorFactoryContext
from ....model.public.modules.file import FileModuleConfiguration
from ...internal.adapters.kernel_module import KernelModule


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
        from ...internal.modules.file import compiler_for

        return compiler_for(configuration, cls)

    @classmethod
    def executor(cls, context: ExecutorFactoryContext) -> Any:
        """Create the executor for this module version."""
        from ...internal.modules.file import executor_for

        return executor_for(context)


__all__ = ["FileModule"]
