"""Serializable execution instructions owned by the core workflow module."""
from __future__ import annotations

from typing import Annotated, Literal, Mapping, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class CoreInstructionIR(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class SourceRelationInstructionIR(CoreInstructionIR):
    action: Literal["source_relation"] = "source_relation"
    relation: str = Field(min_length=1)
    location: str = Field(min_length=1)
    format: Literal["csv", "json", "parquet"]
    credential_reference: str | None = None


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
    if not isinstance(value, Mapping):
        raise ValueError("core workflow steps require an object payload")
    return _INSTRUCTION_ADAPTER.validate_python(value, strict=True)


def encode_core_instruction(value: CoreStepInstructionIR) -> dict[str, object]:
    return value.model_dump(mode="json")


__all__ = [
    "AggregateInstructionIR", "CoreStepInstructionIR",
    "RelationInstructionIR", "SourceRelationInstructionIR",
    "decode_core_instruction", "encode_core_instruction",
]
