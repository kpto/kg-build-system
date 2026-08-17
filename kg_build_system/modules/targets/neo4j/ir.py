"""Serializable execution instructions owned by the Neo4j target."""
from __future__ import annotations

from typing import Annotated, Literal, Mapping, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from ...._frozen_json import FrozenJson, freeze_json, thaw_json


class Neo4jImportIR(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    component: str = Field(min_length=1)
    symbol_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    relative_path: str = Field(min_length=1)
    properties: tuple[str, ...] = ()


class Neo4jNodeImportIR(Neo4jImportIR):
    kind: Literal["node"] = "node"
    id_space: str = Field(min_length=1)


class Neo4jEdgeImportIR(Neo4jImportIR):
    kind: Literal["edge"] = "edge"
    source_id_space: str = Field(min_length=1)
    target_id_space: str = Field(min_length=1)


Neo4jComponentImportIR: TypeAlias = Annotated[
    Neo4jNodeImportIR | Neo4jEdgeImportIR,
    Field(discriminator="kind"),
]


class Neo4jWriteInstructionIR(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    components: tuple[Neo4jComponentImportIR, ...]
    script_name: str = Field(min_length=1)
    default_database: str = Field(min_length=1)


_INSTRUCTION_ADAPTER = TypeAdapter(Neo4jWriteInstructionIR)


def decode_neo4j_instruction(value: object) -> Neo4jWriteInstructionIR:
    value = thaw_json(value)  # type: ignore[arg-type]
    if not isinstance(value, Mapping):
        raise ValueError("Neo4j workflow steps require an object payload")
    return _INSTRUCTION_ADAPTER.validate_python(value)


def encode_neo4j_instruction(value: Neo4jWriteInstructionIR) -> FrozenJson:
    return freeze_json(value.model_dump(mode="json"))


__all__ = [
    "Neo4jComponentImportIR",
    "Neo4jEdgeImportIR",
    "Neo4jNodeImportIR",
    "Neo4jWriteInstructionIR",
    "decode_neo4j_instruction",
    "encode_neo4j_instruction",
]
