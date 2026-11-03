"""The exact-duplicate removal module class."""
from __future__ import annotations

from typing import Any, ClassVar

from .....kernel import ExecutorFactoryContext
from ....model.public.modules.deduplication import DeduplicationConfiguration
from ...internal.adapters.kernel_module import KernelModule


class CollapseExactDuplicatesModule(KernelModule):
    """Drop rows identical in every graph-record column.

    A repeated build key whose values differ is left alone. There is no
    configuration, so registration needs no configuration value.

    Example:
        ```python
        from kg_build_system.distribution import (
            CollapseExactDuplicatesModule, register_module,
        )

        modules = (register_module(CollapseExactDuplicatesModule),)
        ```
    """

    ID: ClassVar[str] = "collapse_exact_duplicates"
    VERSION: ClassVar[str] = "1"
    CONFIGURATION_TYPE: ClassVar[type[DeduplicationConfiguration]] = (
        DeduplicationConfiguration
    )

    @classmethod
    def compiler(cls, configuration: Any) -> Any:
        """Create the compiler for this module version."""
        from ...internal.modules.deduplication import compiler_for

        return compiler_for(configuration, cls)

    @classmethod
    def executor(cls, context: ExecutorFactoryContext) -> Any:
        """Create the executor for this module version."""
        from ...internal.modules.deduplication import executor_for

        return executor_for()


__all__ = ["CollapseExactDuplicatesModule"]
