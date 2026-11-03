"""Instruction DTOs owned by the Neo4j target.

Each typed payload travels under the ``neo4j`` instruction kind the build
dispatcher implements. The component is named by its graph name.
"""
from __future__ import annotations

from typing import Annotated, Literal, Mapping, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .....kernel.internal.json import FrozenObject, thaw_json
from .....pipeline.contract.public import InstructionDTO


class Neo4jImportDTO(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    component: str = Field(min_length=1)
    label: str = Field(min_length=1)
    relative_path: str = Field(min_length=1)
    properties: tuple[str, ...] = ()


class Neo4jNodeImportDTO(Neo4jImportDTO):
    kind: Literal["node"] = "node"
    id_space: str = Field(min_length=1)


class Neo4jEdgeImportDTO(Neo4jImportDTO):
    kind: Literal["edge"] = "edge"
    source_id_space: str = Field(min_length=1)
    target_id_space: str = Field(min_length=1)


Neo4jComponentImportDTO: TypeAlias = Annotated[
    Neo4jNodeImportDTO | Neo4jEdgeImportDTO,
    Field(discriminator="kind"),
]


class Neo4jExportInstructionDTO(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["export_component"] = "export_component"
    component: Neo4jComponentImportDTO


class Neo4jScriptInstructionDTO(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["write_script"] = "write_script"
    components: tuple[Neo4jComponentImportDTO, ...]
    script_name: str = Field(min_length=1)
    default_database: str = Field(min_length=1)


Neo4jInstructionDTO: TypeAlias = Annotated[
    Neo4jExportInstructionDTO | Neo4jScriptInstructionDTO,
    Field(discriminator="kind"),
]


_INSTRUCTION_ADAPTER = TypeAdapter(Neo4jInstructionDTO)


def decode_neo4j_instruction(value: object) -> Neo4jInstructionDTO:
    """Read the typed instruction from its stored or typed form."""
    if isinstance(value, Neo4jExportInstructionDTO | Neo4jScriptInstructionDTO):
        return value
    payload: object = value
    if isinstance(value, InstructionDTO):
        payload = value.payload
    elif hasattr(value, "payload"):
        payload = getattr(value, "payload")
    if isinstance(payload, FrozenObject):
        payload = thaw_json(payload)
    if not isinstance(payload, Mapping):
        raise ValueError("Neo4j workflow steps require an object payload")
    if isinstance(payload.get("payload"), Mapping):
        payload = payload["payload"]
    return _INSTRUCTION_ADAPTER.validate_python(payload)


def encode_neo4j_instruction(value: Neo4jInstructionDTO) -> InstructionDTO:
    """Return one Neo4j instruction in its kind-and-payload form."""
    return InstructionDTO(
        kind="neo4j",
        payload=value.model_dump(mode="json"),
    )


__all__ = [
    "Neo4jComponentImportDTO",
    "Neo4jEdgeImportDTO",
    "Neo4jExportInstructionDTO",
    "Neo4jInstructionDTO",
    "Neo4jNodeImportDTO",
    "Neo4jScriptInstructionDTO",
    "decode_neo4j_instruction",
    "encode_neo4j_instruction",
]
