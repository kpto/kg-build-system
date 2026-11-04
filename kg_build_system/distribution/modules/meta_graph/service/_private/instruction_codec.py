"""Codec for the meta-graph instruction payload."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kg_build_system.kernel.model.internal.json import FrozenObject, thaw_json

from ...model.internal.instruction_dto import MetaGraphDocumentDTO


def decode_meta_graph_instruction(value: object) -> MetaGraphDocumentDTO:
    """Read the typed document payload from an instruction or stored form."""
    if isinstance(value, MetaGraphDocumentDTO):
        return value
    payload: object = value
    if hasattr(value, "payload"):
        payload = getattr(value, "payload")
    if isinstance(payload, FrozenObject):
        payload = thaw_json(payload)
    if not isinstance(payload, Mapping):
        raise ValueError("meta-graph workflow steps require an object payload")
    if isinstance(payload.get("payload"), Mapping):
        payload = payload["payload"]
    return MetaGraphDocumentDTO.model_validate(payload)


def encode_meta_graph_instruction(value: MetaGraphDocumentDTO) -> dict[str, Any]:
    """Return the JSON payload one meta-graph instruction carries."""
    return value.model_dump(mode="json")


__all__ = ["decode_meta_graph_instruction", "encode_meta_graph_instruction"]
