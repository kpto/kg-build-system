"""The exact-duplicate removal module."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from ....kernel import ExecutorFactoryContext
from ...internal.adapters.kernel_module import KernelModule
from ...public.model.registration import ModuleRegistrationConfiguration


@dataclass(frozen=True)
class DeduplicationConfiguration(ModuleRegistrationConfiguration):
    """The operator has no configurable behaviour."""


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
        from ..._private.modules.deduplication.compiler import (
            DeduplicationCompiler,
        )

        return DeduplicationCompiler(configuration)

    @classmethod
    def executor(cls, context: ExecutorFactoryContext) -> Any:
        """Create the executor for this module version."""
        from ..._private.modules.deduplication.executor import (
            DeduplicationExecutor,
        )

        return DeduplicationExecutor()


__all__ = ["CollapseExactDuplicatesModule", "DeduplicationConfiguration"]
