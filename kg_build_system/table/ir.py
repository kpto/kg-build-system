"""Compilation-only IR for logical data declarations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..annotations.ir import AnnotationIR
from ..expressions.ir import ExpressionIR
from ..types.ir import LogicalTypeIR


@dataclass(frozen=True, slots=True)
class FieldIR:
    name: str
    logical_type: LogicalTypeIR
    description: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()


@dataclass(frozen=True, slots=True)
class StructIR:
    symbol_id: str
    name: str
    fields: tuple[FieldIR, ...]
    description: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()


@dataclass(frozen=True, slots=True)
class TableIR:
    symbol_id: str
    name: str
    fields: tuple[FieldIR, ...]
    description: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectionFieldIR:
    name: str
    expression: ExpressionIR
    description: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectionIR:
    symbol_id: str
    name: str
    fields: tuple[ProjectionFieldIR, ...]
    description: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceIR:
    symbol_id: str
    table: str
    location: str
    format: Literal["csv", "json", "parquet"]
    credential_reference: str | None = None
    version: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()


__all__ = [
    "FieldIR",
    "ProjectionIR",
    "ProjectionFieldIR",
    "SourceIR",
    "StructIR",
    "TableIR",
]
