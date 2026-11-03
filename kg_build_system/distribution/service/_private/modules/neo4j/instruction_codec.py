"""Codec for the Neo4j instruction DTOs."""
from __future__ import annotations

from collections.abc import Mapping

from pydantic import TypeAdapter

from kg_build_system.kernel.model.internal.json import FrozenObject, thaw_json
from kg_build_system.pipeline.contract.model.public import InstructionDTO
from .....model.internal.dto.neo4j_instruction_dto import (
    Neo4jExportInstructionDTO,
    Neo4jInstructionDTO,
    Neo4jScriptInstructionDTO,
)

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


__all__ = ["decode_neo4j_instruction", "encode_neo4j_instruction"]
