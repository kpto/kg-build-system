"""Codec for the meta-graph instruction DTOs."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kg_build_system.kernel.model.internal.json import FrozenObject, thaw_json
from kg_build_system.pipeline.contract.model.public import InstructionDTO
from .....model.internal.dto.meta_graph_instruction_dto import (
    MetaGraphDocumentDTO,
)


def decode_meta_graph_instruction(value: object) -> MetaGraphDocumentDTO:
    """Read the typed document payload from its stored or typed form."""
    if isinstance(value, MetaGraphDocumentDTO):
        return value
    payload: object = value
    if isinstance(value, InstructionDTO):
        payload = value.payload
    elif hasattr(value, "payload"):
        payload = getattr(value, "payload")
    if isinstance(payload, FrozenObject):
        payload = thaw_json(payload)
    if not isinstance(payload, Mapping):
        raise ValueError("meta-graph workflow steps require an object payload")
    if isinstance(payload.get("payload"), Mapping):
        payload = payload["payload"]
    return MetaGraphDocumentDTO.model_validate(payload)


def encode_meta_graph_instruction(value: MetaGraphDocumentDTO) -> InstructionDTO:
    """Return one meta-graph instruction in its kind-and-payload form."""
    return InstructionDTO(
        kind="meta_graph",
        payload=value.model_dump(mode="json"),
    )


__all__ = ["decode_meta_graph_instruction", "encode_meta_graph_instruction"]
