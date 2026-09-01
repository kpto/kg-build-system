"""Serializable execution instructions owned by the meta-graph target."""
from __future__ import annotations

from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field

from ...._frozen_json import FrozenJson, freeze_json, thaw_json


class MetaGraphEndpointIR(BaseModel):
    """The endpoint categories an edge component declares."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str = Field(min_length=1)
    target: str = Field(min_length=1)


class MetaGraphBindingIR(BaseModel):
    """One binding targeting a component, with its resolved edge endpoints.

    ``source_node`` and ``target_node`` hold the endpoint the binding actually
    uses — the supplied token, or the declared category when the binding omits
    it — which blueprint validation guarantees to be a concrete node.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol_id: str = Field(min_length=1)
    debug_name: str | None = None
    source_node: str | None = None
    target_node: str | None = None


class MetaGraphPropertyIR(BaseModel):
    """A component property or resolved struct member and its logical type."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    nullable: bool
    logical_type: dict[str, Any]
    description: str | None = None


class MetaGraphComponentIR(BaseModel):
    """One component of the effective topology.

    ``parent`` and ``children`` refer to components by logical name. Blueprint
    validation already requires component logical names to be unique across both
    kinds, so a name is a safe reference; ``symbol_id`` is carried alongside for
    debugging back to the declaring class.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    symbol_id: str = Field(min_length=1)
    kind: Literal["node", "edge"]
    abstract: bool
    label: str = Field(min_length=1)
    description: str | None = None
    parent: str | None = None
    children: tuple[str, ...] = ()
    depth: int = Field(default=0, ge=0)
    endpoints: MetaGraphEndpointIR | None = None
    bindings: tuple[MetaGraphBindingIR, ...] = ()
    properties: tuple[MetaGraphPropertyIR, ...] = ()


class MetaGraphDocumentIR(BaseModel):
    """The static half of the document; record counts arrive at runtime."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1] = 1
    relative_path: str = Field(min_length=1)
    components: tuple[MetaGraphComponentIR, ...] = ()


def decode_meta_graph_instruction(value: object) -> MetaGraphDocumentIR:
    value = thaw_json(value)  # type: ignore[arg-type]
    if not isinstance(value, Mapping):
        raise ValueError("meta-graph workflow steps require an object payload")
    return MetaGraphDocumentIR.model_validate(value)


def encode_meta_graph_instruction(value: MetaGraphDocumentIR) -> FrozenJson:
    return freeze_json(value.model_dump(mode="json"))


__all__ = [
    "MetaGraphBindingIR",
    "MetaGraphComponentIR",
    "MetaGraphDocumentIR",
    "MetaGraphEndpointIR",
    "MetaGraphPropertyIR",
    "decode_meta_graph_instruction",
    "encode_meta_graph_instruction",
]
