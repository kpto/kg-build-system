"""Serializable execution instructions owned by the core workflow module."""
from __future__ import annotations

from typing import Annotated, Any, Literal, Mapping, TypeAlias

from pydantic import (
    BaseModel, BeforeValidator, ConfigDict, Field, TypeAdapter, field_validator,
)

from ..._frozen_json import FrozenJson, freeze_json, thaw_json
from ...types.ir import LogicalTypeIR
from ...types.ir_codec import decode_type_ir, encode_type_ir


def _as_tuple(value: Any) -> Any:
    """A payload arrives as JSON, so a sequence is a tuple by meaning.

    These models validate in strict mode, which would otherwise refuse the
    deserialized list a round-tripped contract carries.
    """
    return tuple(value) if isinstance(value, list) else value


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


class DeclaredColumnIR(CoreInstructionIR):
    """One declared top-level field of a source, with what it is declared to hold.

    ``logical_type`` is the declaration in the JSON form the blueprint uses —
    ``types.ir_codec.encode_type_ir`` out, ``decode_type_ir`` back — because a
    module executor reads the payload and nothing else, and the source view needs
    the declared canonical type to widen the physical column to.
    """

    name: str = Field(min_length=1)
    logical_type: dict[str, Any]

    @field_validator("logical_type")
    @classmethod
    def _declares_a_known_type(cls, value: dict[str, Any]) -> dict[str, Any]:
        decode_type_ir(value)
        return value

    @property
    def logical_type_ir(self) -> LogicalTypeIR:
        """The declared logical type, as the compilation IR states it."""
        return decode_type_ir(self.logical_type)


def encode_declared_column(name: str, logical_type: LogicalTypeIR) -> DeclaredColumnIR:
    """One declared column, carrying the logical type in its JSON form.

    The codec lives here so the payload owns its own carrier: a caller states the
    declaration and ``logical_type_ir`` reads it back.
    """
    return DeclaredColumnIR(name=name, logical_type=encode_type_ir(logical_type))


DeclaredColumns = Annotated[
    tuple[DeclaredColumnIR, ...], BeforeValidator(_as_tuple),
]


class SourceRelationInstructionIR(CoreInstructionIR):
    action: Literal["source_relation"] = "source_relation"
    relation: str = Field(min_length=1)
    location: str = Field(min_length=1)
    format: Literal["csv", "json", "parquet"]
    credential_reference: str | None = None
    #: The logical table this source feeds, named in a shape failure.
    declaration: str = ""
    #: Every top-level field the contract declares, checked against the relation
    #: by name and widened to its declared canonical type where SQL can name it.
    declared_columns: DeclaredColumns = ()
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
    "AggregateInstructionIR", "CoreStepInstructionIR", "DeclaredColumnIR",
    "DeclaredPathIR", "RelationInstructionIR", "SourceRelationInstructionIR",
    "decode_core_instruction", "encode_core_instruction", "encode_declared_column",
]
