"""The values produced by conflict validation."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConflictingNonNullValueFinding:
    """One build key whose non-null property holds more than one value."""

    component: str
    build_key: str
    property_name: str
    distinct_values: int


@dataclass(frozen=True)
class ConflictingNonNullValuesReport:
    """Every finding from one validation run."""

    findings: tuple[ConflictingNonNullValueFinding, ...]


__all__ = [
    "ConflictingNonNullValueFinding",
    "ConflictingNonNullValuesReport",
]
