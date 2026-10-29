"""Compilation-only IR for logical data declarations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

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


_STRUCT_SYMBOL_PREFIX = "python:struct:"


def struct_type_key(struct: StructIR) -> tuple[str, str] | None:
    """Recover the ``(module, qualname)`` identity a struct type refers to.

    A ``StructTypeIR`` names a struct by module and qualified name, and the
    blueprint stores that same identity only inside the struct's symbol ID.
    Two modules may declare same-named structs — names are display, identity
    is this pair — so struct declarations are never resolved by name alone.
    """
    if not struct.symbol_id.startswith(_STRUCT_SYMBOL_PREFIX):
        return None
    module, _, qualname = struct.symbol_id[len(_STRUCT_SYMBOL_PREFIX):].partition(":")
    return (module, qualname) if module and qualname else None


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


JoinHow = Literal["inner", "left", "right", "full"]


@dataclass(frozen=True, slots=True)
class RowScanIR:
    """Read one named table or projection relation."""

    source: str

    @property
    def filters(self) -> tuple[ExpressionIR, ...]:
        """A scan carries no predicates; filters are their own plan node."""
        return ()


@dataclass(frozen=True, slots=True)
class RowFilterIR:
    """Keep the rows of one plan that satisfy a predicate."""

    input: "RowSourcePlanIR"
    predicate: ExpressionIR


@dataclass(frozen=True, slots=True)
class RowUnionIR:
    """Stack two same-shaped plans, optionally deduplicating rows."""

    left: "RowSourcePlanIR"
    right: "RowSourcePlanIR"
    all: bool = True


@dataclass(frozen=True, slots=True)
class RowJoinIR:
    """Equi-join two plans on one expression from each side.

    Null keys never match: the lowerer emits a plain SQL equality, whose
    three-valued result leaves a null key unmatched in every outer-join mode.
    """

    left: "RowSourcePlanIR"
    right: "RowSourcePlanIR"
    left_key: ExpressionIR
    right_key: ExpressionIR
    how: JoinHow = "inner"


@dataclass(frozen=True, slots=True)
class RowGroupByIR:
    """One row per distinct non-null key tuple, with its members collected."""

    input: "RowSourcePlanIR"
    keys: tuple[tuple[str, ExpressionIR], ...]


@dataclass(frozen=True, slots=True)
class RowDistinctIR:
    """Drop duplicate rows while preserving the plan's shape."""

    input: "RowSourcePlanIR"


@dataclass(frozen=True, slots=True)
class RowOrderKeyIR:
    expression: ExpressionIR
    ascending: bool = True


@dataclass(frozen=True, slots=True)
class RowOrderByIR:
    """Order a plan's rows without changing its shape."""

    input: "RowSourcePlanIR"
    keys: tuple[RowOrderKeyIR, ...]


RowSourcePlanIR: TypeAlias = (
    RowScanIR | RowFilterIR | RowUnionIR | RowJoinIR
    | RowGroupByIR | RowDistinctIR | RowOrderByIR
)


@dataclass(frozen=True, slots=True)
class ProjectionIR:
    symbol_id: str
    name: str
    fields: tuple[ProjectionFieldIR, ...]
    description: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()
    row_source: RowSourcePlanIR | None = None


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
    "JoinHow",
    "ProjectionIR",
    "ProjectionFieldIR",
    "RowDistinctIR",
    "RowFilterIR",
    "RowGroupByIR",
    "RowJoinIR",
    "RowOrderByIR",
    "RowOrderKeyIR",
    "RowScanIR",
    "RowSourcePlanIR",
    "RowUnionIR",
    "SourceIR",
    "StructIR",
    "TableIR",
    "struct_type_key",
]
