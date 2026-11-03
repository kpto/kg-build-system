"""Instruction DTOs carried by a distribution step.

A step names its instruction as ``InstructionDTO(kind=..., payload=...)``.
Core contributes typed instructions for the three shapes its executor knows;
they encode to the same kind-and-payload form, so a consumer never needs the
typed class to read one.

The DTO is data: it carries no behaviour and no owner. Its codec lives in
:mod:`kg_build_system.distribution._private.dto.instruction_codec`.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

from pydantic import JsonValue

from ....kernel.internal.types import type_from_document
from ....kernel.internal.types.dto import LogicalTypeDTO


@dataclass(frozen=True, slots=True)
class InstructionDTO:
    """One step instruction as a discriminator and a JSON payload."""

    kind: str
    payload: JsonValue

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or not self.kind:
            raise ValueError("instruction kind must be a non-empty string")


@dataclass(frozen=True, slots=True)
class DeclaredPathDTO:
    """One declared member path, in both forms the source step needs."""

    schema_path: str
    logical_path: str

    def __post_init__(self) -> None:
        if not self.schema_path:
            raise ValueError("declared schema paths must be non-empty")
        if not self.logical_path:
            raise ValueError("declared logical paths must be non-empty")


@dataclass(frozen=True, slots=True)
class DeclaredColumnDTO:
    """One declared top-level field, with the type it is declared to hold."""

    name: str
    logical_type: dict[str, Any]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("declared columns require a non-empty name")
        if not isinstance(self.logical_type, Mapping):
            raise ValueError("declared column types must be objects")
        type_from_document(self.logical_type)
        object.__setattr__(self, "logical_type", dict(self.logical_type))


@dataclass(frozen=True, slots=True)
class SourceRelationInstructionDTO:
    """Read one physical source and expose its widened, typed relation."""

    relation: str
    location: str
    format: Literal["csv", "json", "parquet"]
    credential_reference: str | None = None
    declaration: str = ""
    declared_columns: tuple[DeclaredColumnDTO, ...] = ()
    declared_paths: tuple[DeclaredPathDTO, ...] = ()
    kind: Literal["source_relation"] = "source_relation"

    def __post_init__(self) -> None:
        for value, label in (
            (self.relation, "relation"),
            (self.location, "location"),
        ):
            if not value:
                raise ValueError(f"source instructions require a non-empty {label}")
        if self.format not in {"csv", "json", "parquet"}:
            raise ValueError(f"unknown source format {self.format!r}")
        object.__setattr__(self, "declared_columns", tuple(self.declared_columns))
        object.__setattr__(self, "declared_paths", tuple(self.declared_paths))


@dataclass(frozen=True, slots=True)
class RelationInstructionDTO:
    """Define one named relation from SQL the module already emitted."""

    relation: str
    sql: str
    kind: Literal["relation"] = "relation"

    def __post_init__(self) -> None:
        if not self.relation:
            raise ValueError("relation instructions require a non-empty relation")
        if not self.sql:
            raise ValueError("relation instructions require non-empty SQL")


@dataclass(frozen=True, slots=True)
class AggregateInstructionDTO:
    """Union every binding relation of one bound component into graph records."""

    relation: str
    kind: Literal["aggregate"] = "aggregate"

    def __post_init__(self) -> None:
        if not self.relation:
            raise ValueError("aggregate instructions require a non-empty relation")


CoreInstructionDTO: TypeAlias = (
    SourceRelationInstructionDTO | RelationInstructionDTO | AggregateInstructionDTO
)


__all__ = [
    "AggregateInstructionDTO",
    "CoreInstructionDTO",
    "DeclaredColumnDTO",
    "DeclaredPathDTO",
    "InstructionDTO",
    "RelationInstructionDTO",
    "SourceRelationInstructionDTO",
]
