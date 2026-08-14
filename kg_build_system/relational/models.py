"""Immutable logical relational plans produced from canonical expressions."""
from __future__ import annotations

from dataclasses import dataclass

from ..expressions import ExpressionNode


@dataclass(frozen=True, slots=True)
class Scan:
    source: str
    relation: str
    alias: str


@dataclass(frozen=True, slots=True)
class Expand:
    scope: tuple[str, ...]
    expression: ExpressionNode
    alias: str


@dataclass(frozen=True, slots=True)
class Filter:
    expression: ExpressionNode


@dataclass(frozen=True, slots=True)
class RelationPlan:
    """One self-contained row context and its named output expressions."""

    scans: tuple[Scan, ...]
    expands: tuple[Expand, ...]
    filters: tuple[Filter, ...]
    outputs: tuple[tuple[str, ExpressionNode], ...]


__all__ = ["Expand", "Filter", "RelationPlan", "Scan"]
