"""Instruction DTOs owned by the meta-graph target.

The static half of the document is a typed payload. It travels under the
``meta_graph`` instruction kind the build dispatcher implements.
"""
from __future__ import annotations

from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field

from .....kernel.internal.json import FrozenObject, thaw_json
from .....pipeline.contract.public import InstructionDTO


class MetaGraphEndpointDTO(BaseModel):
    """The endpoint categories an edge component declares."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str = Field(min_length=1)
    target: str = Field(min_length=1)


class MetaGraphBindingDTO(BaseModel):
    """One binding targeting a component, with its resolved edge endpoints."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    debug_name: str | None = None
    source_node: str | None = None
    target_node: str | None = None


class MetaGraphPropertyDTO(BaseModel):
    """A component property or resolved struct member and its logical type."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    nullable: bool
    logical_type: dict[str, Any]
    description: str | None = None
    annotations: tuple[dict[str, Any], ...] = ()


class MetaGraphComponentDTO(BaseModel):
    """One component of the effective topology."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    kind: Literal["node", "edge"]
    abstract: bool
    label: str = Field(min_length=1)
    labels: tuple[str, ...] = ()
    description: str | None = None
    parent: str | None = None
    children: tuple[str, ...] = ()
    depth: int = Field(default=0, ge=0)
    source: str | None = None
    target: str | None = None
    endpoints: MetaGraphEndpointDTO | None = None
    bindings: tuple[MetaGraphBindingDTO, ...] = ()
    properties: tuple[MetaGraphPropertyDTO, ...] = ()
    annotations: tuple[dict[str, Any], ...] = ()


class MetaGraphDocumentDTO(BaseModel):
    """The static half of the document; counts and example values are runtime."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    relative_path: str = Field(min_length=1)
    example_limit: int = Field(default=3, ge=0)
    include_html: bool = True
    html_relative_path: str = Field(default="meta_graph.html", min_length=1)
    components: tuple[MetaGraphComponentDTO, ...] = ()


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


__all__ = [
    "MetaGraphBindingDTO",
    "MetaGraphComponentDTO",
    "MetaGraphDocumentDTO",
    "MetaGraphEndpointDTO",
    "MetaGraphPropertyDTO",
    "decode_meta_graph_instruction",
    "encode_meta_graph_instruction",
]
