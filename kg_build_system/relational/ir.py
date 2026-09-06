"""Compilation-only IR for engine-neutral relational plans."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..expressions.ir import ExpressionIR


@dataclass(frozen=True, slots=True)
class ScanIR:
    source: str
    relation: str
    alias: str


@dataclass(frozen=True, slots=True)
class ExpandIR:
    scope: tuple[str, ...]
    expression: ExpressionIR
    alias: str


@dataclass(frozen=True, slots=True)
class FilterIR:
    expression: ExpressionIR
    mode: Literal["present", "true"] = "present"


@dataclass(frozen=True, slots=True)
class RelationPlanIR:
    scans: tuple[ScanIR, ...]
    expands: tuple[ExpandIR, ...]
    filters: tuple[FilterIR, ...]
    outputs: tuple[tuple[str, ExpressionIR], ...]


__all__ = ["ExpandIR", "FilterIR", "RelationPlanIR", "ScanIR"]
