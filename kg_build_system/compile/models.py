"""Immutable compiled-definition models."""
from dataclasses import dataclass
from ..binding import EdgeBinding, NodeBinding
from ..data import BoundTable

Binding = NodeBinding | EdgeBinding

@dataclass(frozen=True)
class CompiledGraphDefinition:
    bindings: tuple[Binding, ...]
    projections: tuple[type, ...] = ()

@dataclass(frozen=True)
class CompiledBuildDefinition:
    graph: CompiledGraphDefinition
    sources: tuple[BoundTable, ...]
    sql: str
    target: object
