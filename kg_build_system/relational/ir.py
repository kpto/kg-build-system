"""Compilation-only IR for engine-neutral relation plans."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..expressions.ir import ExpressionIR


@dataclass(frozen=True, slots=True)
class ScanIR:
    """Read one materialised relation under one plan-local alias."""

    source: str
    relation: str
    alias: str


@dataclass(frozen=True, slots=True)
class ExpandIR:
    """Fan one array expression out into rows under a stable scope."""

    scope: tuple[str, ...]
    expression: ExpressionIR
    alias: str


@dataclass(frozen=True, slots=True)
class FilterIR:
    """Keep rows whose expression is present, or whose predicate is true."""

    expression: ExpressionIR
    mode: Literal["present", "true"] = "present"


@dataclass(frozen=True, slots=True)
class RelationPlanIR:
    """One projection or binding: its scans, row effects and outputs."""

    scans: tuple[ScanIR, ...]
    expands: tuple[ExpandIR, ...]
    filters: tuple[FilterIR, ...]
    outputs: tuple[tuple[str, ExpressionIR], ...]


__all__ = ["ExpandIR", "FilterIR", "RelationPlanIR", "ScanIR"]
