"""The conflicting-non-null-value validation planner's configuration."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConflictValidationConfiguration:
    """Choose whether a conflicting non-null value fails the build or is reported.

    With ``fail_on_error=True`` (the default), any finding fails the run. With
    ``False``, the records continue to later planners and a report is published.

    Example:
        ```python
        from kg_build_system.distribution import (
            ConflictValidationConfiguration,
        )

        configuration = ConflictValidationConfiguration(fail_on_error=False)
        ```
    """

    fail_on_error: bool = True


__all__ = ["ConflictValidationConfiguration"]
