"""The data language's part of the graph blueprint.

The DTO states the semantic model: structs, relations, projection outputs and
the row plans that read them. Every cross-symbol reference is a typed ref: a
column names its field symbol, a scan names a relation and a relation names the
logical asset it is read from. It carries graph names and canonical values only;
it has no symbol id, Python module path or declaration object.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from kg_build_system.distribution.languages.annotations.model.internal import AnnotationDTO
from kg_build_system.distribution.languages.expressions.model.internal.dto.blueprint_dto import ExpressionDTO
from kg_build_system.distribution.model.public.refs import (
    AssetRef, FieldRef, RelationRef,
)
from kg_build_system.kernel.model.internal.types.dto import LogicalTypeDTO


@dataclass(frozen=True, slots=True)
class ColumnDTO:
    """One named column of a struct, relation or projection output.

    Example:
        ```python
        from kg_build_system.distribution.languages.data.model.internal import (
            ColumnDTO,
        )
        from kg_build_system.distribution.model.public.refs import FieldRef
        from kg_build_system.kernel import Key
        from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO

        column = ColumnDTO(
            "site_name",
            UnitTypeDTO("str"),
            ref=FieldRef("data", Key(("sites.site_name",))),
        )
        ```
    """

    name: str
    logical_type: LogicalTypeDTO
    ref: FieldRef
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
    """A named logical table relation read from one logical asset."""

    name: str
    columns: tuple[ColumnDTO, ...]
    asset: AssetRef
    description: str | None = None
    annotations: tuple[AnnotationDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class RowScanDTO:
    """Read one declared relation or projection.

    Example:
        ```python
        from kg_build_system.distribution.languages.data.model.internal import (
            RowScanDTO,
        )
        from kg_build_system.distribution.model.public.refs import RelationRef
        from kg_build_system.kernel import Key

        scan = RowScanDTO(RelationRef("data", Key(("sites",))))
        ```
    """

    relation: RelationRef


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


@dataclass(frozen=True, slots=True)
class RowUnnestDTO:
    """Expand one array field into rows, keeping the other fields.

    ``field`` is the external column name whose array value is expanded and
    ``expression`` is that array in the input plan. A null or empty array
    produces no rows.
    """

    input: "RowSourcePlanDTO"
    field: str
    expression: ExpressionDTO


RowSourcePlanDTO: TypeAlias = (
    RowScanDTO | RowFilterDTO | RowUnionDTO | RowJoinDTO
    | RowGroupByDTO | RowDistinctDTO | RowOrderByDTO | RowUnnestDTO
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
class DataPartDTO:
    """The data language part of a blueprint."""

    structs: tuple[StructDTO, ...]
    relations: tuple[RelationDTO, ...]
    projections: tuple[ProjectionDTO, ...]


__all__ = [
    "ColumnDTO", "DataPartDTO", "ProjectionDTO", "RelationDTO",
    "RowDistinctDTO", "RowFilterDTO", "RowGroupByDTO", "RowJoinDTO",
    "RowOrderByDTO", "RowScanDTO", "RowSourcePlanDTO", "RowUnionDTO",
    "RowUnnestDTO", "StructDTO",
]
