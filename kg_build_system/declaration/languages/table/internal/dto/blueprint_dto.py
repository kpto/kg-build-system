"""The table language's part of the graph blueprint.

The DTO states the semantic model: structs, relations, projection outputs,
physical sources and the row plans that read them. It carries graph names and
canonical values only; it has no symbol id, Python module path or declaration
object.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from kg_build_system.declaration.foundations.annotations.internal import AnnotationDTO
from kg_build_system.declaration.foundations.expressions.internal.dto.blueprint_dto import (
    ExpressionDTO,
)
from kg_build_system.kernel.internal.types.dto import LogicalTypeDTO


@dataclass(frozen=True, slots=True)
class ColumnDTO:
    """One named column of a struct, relation or projection output."""

    name: str
    logical_type: LogicalTypeDTO
    description: str | None = None
    annotations: tuple[AnnotationDTO, ...] = ()
    expression: ExpressionDTO | None = None


@dataclass(frozen=True, slots=True)
class StructDTO:
    """A value record assembled from source-backed members."""

    name: str
    columns: tuple[ColumnDTO, ...]
    description: str | None = None
    annotations: tuple[AnnotationDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class RelationDTO:
    """A named logical table relation."""

    name: str
    columns: tuple[ColumnDTO, ...]
    description: str | None = None
    annotations: tuple[AnnotationDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class RowScanDTO:
    """Read one named relation."""

    source: str


@dataclass(frozen=True, slots=True)
class RowFilterDTO:
    """Keep the rows of one plan that satisfy a predicate."""

    input: "RowSourcePlanDTO"
    predicate: ExpressionDTO


@dataclass(frozen=True, slots=True)
class RowUnionDTO:
    """Stack two same-shaped plans, optionally deduplicating rows."""

    left: "RowSourcePlanDTO"
    right: "RowSourcePlanDTO"
    all: bool = True


@dataclass(frozen=True, slots=True)
class RowJoinDTO:
    """Equi-join two plans on one expression from each side."""

    left: "RowSourcePlanDTO"
    right: "RowSourcePlanDTO"
    left_key: ExpressionDTO
    right_key: ExpressionDTO
    how: Literal["inner", "left", "right", "full"] = "inner"


@dataclass(frozen=True, slots=True)
class RowGroupByDTO:
    """One row per distinct non-null key tuple, with its members collected."""

    input: "RowSourcePlanDTO"
    keys: tuple[tuple[str, ExpressionDTO], ...]


@dataclass(frozen=True, slots=True)
class RowDistinctDTO:
    """Drop duplicate rows while preserving the plan's shape."""

    input: "RowSourcePlanDTO"


@dataclass(frozen=True, slots=True)
class RowOrderByDTO:
    """Order a plan's rows without changing its shape."""

    input: "RowSourcePlanDTO"
    keys: tuple[tuple[ExpressionDTO, bool], ...]


RowSourcePlanDTO: TypeAlias = (
    RowScanDTO | RowFilterDTO | RowUnionDTO | RowJoinDTO
    | RowGroupByDTO | RowDistinctDTO | RowOrderByDTO
)


@dataclass(frozen=True, slots=True)
class ProjectionDTO:
    """A named logical relation whose columns are expressions."""

    name: str
    columns: tuple[ColumnDTO, ...]
    row_source: RowSourcePlanDTO
    description: str | None = None
    annotations: tuple[AnnotationDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceDTO:
    """The physical source one relation is read from."""

    table: str
    location: str
    format: Literal["csv", "json", "parquet"]
    credential_reference: str | None = None
    version: str | None = None
    annotations: tuple[AnnotationDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class DataPartDTO:
    """The table language part of a blueprint."""

    structs: tuple[StructDTO, ...]
    relations: tuple[RelationDTO, ...]
    projections: tuple[ProjectionDTO, ...]
    sources: tuple[SourceDTO, ...]


__all__ = [
    "ColumnDTO", "DataPartDTO", "ProjectionDTO", "RelationDTO",
    "RowDistinctDTO", "RowFilterDTO", "RowGroupByDTO", "RowJoinDTO",
    "RowOrderByDTO", "RowScanDTO", "RowSourcePlanDTO", "RowUnionDTO",
    "SourceDTO", "StructDTO",
]
