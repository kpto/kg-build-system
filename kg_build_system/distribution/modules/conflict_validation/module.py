"""The conflicting-non-null-value validation module."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from ....kernel import ExecutorFactoryContext
from ...internal.adapters.kernel_module import KernelModule
from ...public.model.registration import ModuleRegistrationConfiguration


@dataclass(frozen=True)
class RejectConflictingNonNullValuesConfiguration(ModuleRegistrationConfiguration):
    """Choose whether a conflicting non-null value fails the build or is reported.

    With ``fail_on_error=True`` (the default), any finding fails the run. With
    ``False``, the records continue to later modules and a report is published.

    Example:
        ```python
        from kg_build_system.distribution import (
            RejectConflictingNonNullValuesConfiguration,
            RejectConflictingNonNullValuesModule, register_module,
        )

        modules = (
            register_module(
                RejectConflictingNonNullValuesModule,
                RejectConflictingNonNullValuesConfiguration(fail_on_error=False),
            ),
        )
        ```
    """

    fail_on_error: bool = True


@dataclass(frozen=True)
class ConflictingNonNullValueFinding:
    component: str
    build_key: str
    property_name: str
    distinct_values: int


@dataclass(frozen=True)
class ConflictingNonNullValuesReport:
    findings: tuple[ConflictingNonNullValueFinding, ...]


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
        from .compiler import ConflictValidationCompiler

        return ConflictValidationCompiler(configuration)

    @classmethod
    def executor(cls, context: ExecutorFactoryContext) -> Any:
        """Create the executor for this module version."""
        from .executor import ConflictValidationExecutor

        return ConflictValidationExecutor()


__all__ = [
    "ConflictingNonNullValueFinding",
    "ConflictingNonNullValuesReport",
    "RejectConflictingNonNullValuesConfiguration",
    "RejectConflictingNonNullValuesModule",
]
