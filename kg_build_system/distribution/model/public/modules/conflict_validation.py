"""The conflicting-non-null-value module's configuration and report data."""
from __future__ import annotations

from dataclasses import dataclass

from ..registration import ModuleRegistrationConfiguration


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


__all__ = [
    "ConflictingNonNullValueFinding",
    "ConflictingNonNullValuesReport",
    "RejectConflictingNonNullValuesConfiguration",
]
