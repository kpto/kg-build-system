"""Compilation-only transfer objects for engine-neutral relational plans."""
from __future__ import annotations

from dataclasses import dataclass

from ..expressions.dto import ExpressionDTO


@dataclass(frozen=True, slots=True)
class ScanDTO:
    source: str
    relation: str
    alias: str


@dataclass(frozen=True, slots=True)
class ExpandDTO:
    scope: tuple[str, ...]
    expression: ExpressionDTO
    alias: str


@dataclass(frozen=True, slots=True)
class FilterDTO:
    expression: ExpressionDTO


@dataclass(frozen=True, slots=True)
class RelationPlanDTO:
    scans: tuple[ScanDTO, ...]
    expands: tuple[ExpandDTO, ...]
    filters: tuple[FilterDTO, ...]
    outputs: tuple[tuple[str, ExpressionDTO], ...]


__all__ = ["ExpandDTO", "FilterDTO", "RelationPlanDTO", "ScanDTO"]
