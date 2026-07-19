"""Portable, serialisable models for declarative graph bindings."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass

from kg_build_system.binding.schema import BindingValidationError, Table


@dataclass(frozen=True, slots=True)
class FieldMapping:
    """Maps one topology field to one field in an input table."""

    target: str
    source: str

    def __post_init__(self) -> None:
        if not self.target or not self.source:
            raise BindingValidationError("Binding mapping targets and sources must be non-empty.")

    def to_dict(self) -> dict[str, str]:
        return {"target": self.target, "source": self.source}


@dataclass(frozen=True, slots=True)
class NodeBindingDefinition:
    """A portable binding that produces records for one node type."""

    target: str
    table: Table
    mappings: Sequence[FieldMapping]

    def __post_init__(self) -> None:
        if not self.target:
            raise BindingValidationError("Node binding targets must be non-empty.")
        object.__setattr__(self, "mappings", tuple(self.mappings))

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "node",
            "target": self.target,
            "table": self.table.to_dict(),
            "mappings": [mapping.to_dict() for mapping in self.mappings],
        }


@dataclass(frozen=True, slots=True)
class EdgeBindingDefinition:
    """A portable binding that produces records for one edge type."""

    target: str
    table: Table
    source: str
    target_endpoint: str
    mappings: Sequence[FieldMapping]

    def __post_init__(self) -> None:
        if not self.target or not self.source or not self.target_endpoint:
            raise BindingValidationError("Edge binding targets and endpoints must be non-empty.")
        object.__setattr__(self, "mappings", tuple(self.mappings))

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "edge",
            "target": self.target,
            "table": self.table.to_dict(),
            "source": self.source,
            "target_endpoint": self.target_endpoint,
            "mappings": [mapping.to_dict() for mapping in self.mappings],
        }


@dataclass(frozen=True, slots=True)
class BindingSet:
    """The serialisable collection of portable bindings for a graph build."""

    name: str
    node_bindings: Sequence[NodeBindingDefinition]
    edge_bindings: Sequence[EdgeBindingDefinition]

    def __post_init__(self) -> None:
        if not self.name:
            raise BindingValidationError("Binding set names must be non-empty.")
        object.__setattr__(self, "node_bindings", tuple(self.node_bindings))
        object.__setattr__(self, "edge_bindings", tuple(self.edge_bindings))

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "node_bindings": [binding.to_dict() for binding in self.node_bindings],
            "edge_bindings": [binding.to_dict() for binding in self.edge_bindings],
        }

    def to_json(self, *, indent: int = 2) -> str:
        """Return the portable JSON representation of these bindings."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"
