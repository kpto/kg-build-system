"""The compatible-facts merging module class."""
from __future__ import annotations

from typing import Any, ClassVar

from .....kernel import ExecutorFactoryContext
from ....model.public.modules.merging import (
    MergeCompatibleFactsModuleConfiguration,
)
from ...internal.adapters.kernel_module import KernelModule


class MergeCompatibleFactsModule(KernelModule):
    """Fold same-key graph records into one, keeping the minimum value.

    The operator is only sound when parallel same-key rows express one fact.
    ``MergeCompatibleFactsModuleConfiguration`` selects the components.

    Example:
        ```python
        from kg_build_system.distribution import (
            MergeCompatibleFactsModule,
            MergeCompatibleFactsModuleConfiguration, register_module,
        )

        modules = (
            register_module(
                MergeCompatibleFactsModule,
                MergeCompatibleFactsModuleConfiguration(),
            ),
        )
        ```
    """

    ID: ClassVar[str] = "merge_compatible_facts"
    VERSION: ClassVar[str] = "1"
    CONFIGURATION_TYPE: ClassVar[type[MergeCompatibleFactsModuleConfiguration]] = (
        MergeCompatibleFactsModuleConfiguration
    )

    @classmethod
    def compiler(cls, configuration: Any) -> Any:
        """Create the compiler for this module version."""
        from ...internal.modules.merging import compiler_for

        return compiler_for(configuration, cls)

    @classmethod
    def executor(cls, context: ExecutorFactoryContext) -> Any:
        """Create the executor for this module version."""
        from ...internal.modules.merging import executor_for

        return executor_for()


__all__ = ["MergeCompatibleFactsModule"]
