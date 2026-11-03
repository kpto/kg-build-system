"""Engine-neutral relation plans.

A plan names the relations it reads, the row effects it applies and the outputs
it produces. It contains no SQL and no engine value.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from kg_build_system.declaration.foundations.expressions.model.internal.dto import ExpressionDTO


@dataclass(frozen=True, slots=True)
class Scan:
    """Read one materialised relation under one plan-local alias."""

    source: str
    relation: str
    alias: str


@dataclass(frozen=True, slots=True)
class Expand:
    """Fan one array expression out into rows under a stable scope."""

    scope: tuple[str, ...]
    expression: ExpressionDTO
    alias: str


@dataclass(frozen=True, slots=True)
class Filter:
    """Keep rows whose expression is present, or whose predicate is true."""

    expression: ExpressionDTO
    mode: Literal["present", "true"] = "present"


@dataclass(frozen=True, slots=True)
class RelationPlan:
    """One projection or binding: its scans, row effects and outputs."""

    scans: tuple[Scan, ...]
    expands: tuple[Expand, ...]
    filters: tuple[Filter, ...]
    outputs: tuple[tuple[str, ExpressionDTO], ...]


__all__ = ["Expand", "Filter", "RelationPlan", "Scan"]
