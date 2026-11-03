"""The conflicting-non-null-value validation module class."""
from __future__ import annotations

from typing import Any, ClassVar

from .....kernel import ExecutorFactoryContext
from ....model.public.modules.conflict_validation import (
    RejectConflictingNonNullValuesConfiguration,
)
from ...internal.adapters.kernel_module import KernelModule


class RejectConflictingNonNullValuesModule(KernelModule):
    """Reject more than one distinct non-null value per key and property.

    Nulls never create a conflict. ``RejectConflictingNonNullValuesConfiguration``
    chooses whether findings fail the run or are published as a report.

    Example:
        ```python
        from kg_build_system.distribution import (
            RejectConflictingNonNullValuesModule, register_module,
        )

        modules = (register_module(RejectConflictingNonNullValuesModule),)
        ```
    """

    ID: ClassVar[str] = "reject_conflicting_non_null_values"
    VERSION: ClassVar[str] = "1"
    CONFIGURATION_TYPE: ClassVar[
        type[RejectConflictingNonNullValuesConfiguration]
    ] = RejectConflictingNonNullValuesConfiguration

    @classmethod
    def compiler(cls, configuration: Any) -> Any:
        """Create the compiler for this module version."""
        from ...internal.modules.conflict_validation import compiler_for

        return compiler_for(configuration, cls)

    @classmethod
    def executor(cls, context: ExecutorFactoryContext) -> Any:
        """Create the executor for this module version."""
        from ...internal.modules.conflict_validation import executor_for

        return executor_for()


__all__ = ["RejectConflictingNonNullValuesModule"]
