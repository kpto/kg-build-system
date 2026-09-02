"""Serializable execution instructions owned by the core workflow module."""
from __future__ import annotations

from typing import Annotated, Any, Literal, Mapping, TypeAlias

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, TypeAdapter


def _as_tuple(value: Any) -> Any:
    """A payload arrives as JSON, so a sequence is a tuple by meaning.

    These models validate in strict mode, which would otherwise refuse the
    deserialized list a round-tripped contract carries.
    """
    return tuple(value) if isinstance(value, list) else value


FrozenTuple = Annotated[tuple[str, ...], BeforeValidator(_as_tuple)]

from ..._frozen_json import FrozenJson, freeze_json, thaw_json


class CoreInstructionIR(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class DeclaredPathIR(BaseModel):
    """One declared member path, in both forms the source step needs.

    A module executor never sees the blueprint, so what the contract knows about a
    contract has to travel in the step payload — the same way the meta-graph
    module ships its static topology.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    #: Dotted path as ``parquet_metadata()`` reports it in ``path_in_schema``,
    #: including the Parquet list wrappers.
    schema_path: str = Field(min_length=1)
    #: The same path without the list wrappers, for people.
    logical_path: str = Field(min_length=1)


DeclaredPaths = Annotated[
    tuple[DeclaredPathIR, ...], BeforeValidator(_as_tuple),
]


class SourceRelationInstructionIR(CoreInstructionIR):
    action: Literal["source_relation"] = "source_relation"
    relation: str = Field(min_length=1)
    location: str = Field(min_length=1)
    format: Literal["csv", "json", "parquet"]
    credential_reference: str | None = None
    #: The logical table this source feeds, named in a shape failure.
    declaration: str = ""
    #: Every top-level field the contract declares, checked against the relation.
    declared_columns: FrozenTuple = ()
    #: Paths the build reads that claim non-nullability, for the statistics
    #: pre-flight. Absent statistics are reported as unknown, never as zero.
    declared_paths: DeclaredPaths = ()


class RelationInstructionIR(CoreInstructionIR):
    action: Literal["relation"] = "relation"
    relation: str = Field(min_length=1)
    sql: str = Field(min_length=1)


class AggregateInstructionIR(CoreInstructionIR):
    action: Literal["aggregate"] = "aggregate"
    relation: str = Field(min_length=1)


CoreStepInstructionIR: TypeAlias = Annotated[
    SourceRelationInstructionIR | RelationInstructionIR | AggregateInstructionIR,
    Field(discriminator="action"),
]

_INSTRUCTION_ADAPTER = TypeAdapter(CoreStepInstructionIR)


def decode_core_instruction(value: object) -> CoreStepInstructionIR:
    value = thaw_json(value)  # type: ignore[arg-type]
    if not isinstance(value, Mapping):
        raise ValueError("core workflow steps require an object payload")
    return _INSTRUCTION_ADAPTER.validate_python(value, strict=True)


def encode_core_instruction(value: CoreStepInstructionIR) -> FrozenJson:
    return freeze_json(value.model_dump(mode="json"))


__all__ = [
    "AggregateInstructionIR", "CoreStepInstructionIR", "DeclaredPathIR",
    "RelationInstructionIR", "SourceRelationInstructionIR",
    "decode_core_instruction", "encode_core_instruction",
]
