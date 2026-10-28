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


@dataclass(frozen=True, slots=True)
class RowSourcePlanIR:
    source: str
    filters: tuple[ExpressionIR, ...] = ()


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
    "ProjectionIR",
    "ProjectionFieldIR",
    "RowSourcePlanIR",
    "SourceIR",
    "StructIR",
    "TableIR",
    "struct_type_key",
]
