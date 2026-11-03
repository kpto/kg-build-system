"""The compatible-facts merging module."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from ....kernel import ExecutorFactoryContext
from ...internal.adapters.kernel_module import KernelModule
from ...public.model.registration import ModuleRegistrationConfiguration


@dataclass(frozen=True)
class MergeCompatibleFactsModuleConfiguration(ModuleRegistrationConfiguration):
    """``components=None`` merges every record component; a tuple restricts the
    operator to those component classes, leaving every other component's records
    untouched by this step.

    Merging folds same-key rows into one record (a ``min()`` per column), so it
    is only sound for components whose parallel same-key rows are meant to be one
    fact. Edge families that deliberately keep parallel facts stay outside the
    scope.

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

    components: tuple[type[Any], ...] | None = None

    def __post_init__(self) -> None:
        from ..._private.modules.merging.configuration import resolve_components

        object.__setattr__(self, "components", resolve_components(self.components))

    def to_json(self) -> Any:
        from ..._private.modules.merging.configuration import components_json

        return components_json(self.components)


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
        from ..._private.modules.merging.compiler import MergingCompiler

        return MergingCompiler(configuration)

    @classmethod
    def executor(cls, context: ExecutorFactoryContext) -> Any:
        """Create the executor for this module version."""
        from ..._private.modules.merging.executor import MergingExecutor

        return MergingExecutor()


__all__ = [
    "MergeCompatibleFactsModule",
    "MergeCompatibleFactsModuleConfiguration",
]
