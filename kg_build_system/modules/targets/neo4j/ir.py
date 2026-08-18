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


class Neo4jExportInstructionIR(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    action: Literal["export_component"] = "export_component"
    component: Neo4jComponentImportIR


class Neo4jScriptInstructionIR(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    action: Literal["write_script"] = "write_script"
    components: tuple[Neo4jComponentImportIR, ...]
    script_name: str = Field(min_length=1)
    default_database: str = Field(min_length=1)


Neo4jInstructionIR: TypeAlias = Annotated[
    Neo4jExportInstructionIR | Neo4jScriptInstructionIR,
    Field(discriminator="action"),
]


_INSTRUCTION_ADAPTER = TypeAdapter(Neo4jInstructionIR)


def decode_neo4j_instruction(value: object) -> Neo4jInstructionIR:
    value = thaw_json(value)  # type: ignore[arg-type]
    if not isinstance(value, Mapping):
        raise ValueError("Neo4j workflow steps require an object payload")
    return _INSTRUCTION_ADAPTER.validate_python(value)


def encode_neo4j_instruction(value: Neo4jInstructionIR) -> FrozenJson:
    return freeze_json(value.model_dump(mode="json"))


__all__ = [
    "Neo4jComponentImportIR",
    "Neo4jEdgeImportIR",
    "Neo4jExportInstructionIR",
    "Neo4jInstructionIR",
    "Neo4jNodeImportIR",
    "Neo4jScriptInstructionIR",
    "decode_neo4j_instruction",
    "encode_neo4j_instruction",
]
