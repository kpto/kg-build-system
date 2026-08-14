"""Compilation-only transfer objects for logical data declarations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..annotations.dto import AnnotationDTO
from ..expressions.dto import ExpressionDTO
from ..types.dto import LogicalTypeDTO


@dataclass(frozen=True, slots=True)
class FieldDTO:
    name: str
    logical_type: LogicalTypeDTO
    description: str | None = None
    annotations: tuple[AnnotationDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class StructDTO:
    symbol_id: str
    name: str
    fields: tuple[FieldDTO, ...]
    description: str | None = None
    annotations: tuple[AnnotationDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class TableDTO:
    symbol_id: str
    name: str
    fields: tuple[FieldDTO, ...]
    description: str | None = None
    annotations: tuple[AnnotationDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectionFieldDTO:
    name: str
    expression: ExpressionDTO
    description: str | None = None
    annotations: tuple[AnnotationDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectionDTO:
    symbol_id: str
    name: str
    fields: tuple[ProjectionFieldDTO, ...]
    description: str | None = None
    annotations: tuple[AnnotationDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceDTO:
    symbol_id: str
    table: str
    location: str
    format: Literal["csv", "json", "parquet"]
    credential_reference: str | None = None
    version: str | None = None
    annotations: tuple[AnnotationDTO, ...] = ()


__all__ = [
    "FieldDTO",
    "ProjectionDTO",
    "ProjectionFieldDTO",
    "SourceDTO",
    "StructDTO",
    "TableDTO",
]
