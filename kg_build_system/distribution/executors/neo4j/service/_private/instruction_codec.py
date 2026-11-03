"""Codec for the Neo4j instruction payloads."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import TypeAdapter

from kg_build_system.kernel.model.internal.json import FrozenObject, thaw_json

from ...model.internal.instruction_dto import (
    Neo4jExportInstructionDTO,
    Neo4jInstructionDTO,
    Neo4jScriptInstructionDTO,
)

_INSTRUCTION_ADAPTER = TypeAdapter(Neo4jInstructionDTO)


def decode_neo4j_instruction(value: object) -> Neo4jInstructionDTO:
    """Read the typed instruction from an instruction, mapping or typed value."""
    if isinstance(value, Neo4jExportInstructionDTO | Neo4jScriptInstructionDTO):
        return value
    payload: Any = value
    if hasattr(value, "payload"):
        payload = getattr(value, "payload")
    if isinstance(payload, FrozenObject):
        payload = thaw_json(payload)
    if not isinstance(payload, Mapping):
        raise ValueError("Neo4j workflow steps require an object payload")
    nested = payload.get("payload")
    if isinstance(nested, Mapping):
        payload = nested
    data: dict[str, Any] = dict(payload)
    # The bundle directory is executor context, not part of the typed
    # component/script instruction.
    data.pop("relative_directory", None)
    return _INSTRUCTION_ADAPTER.validate_python(data)


def encode_neo4j_instruction(value: Neo4jInstructionDTO) -> dict[str, Any]:
    """Return the JSON payload one Neo4j instruction carries."""
    return value.model_dump(mode="json")


__all__ = ["decode_neo4j_instruction", "encode_neo4j_instruction"]
