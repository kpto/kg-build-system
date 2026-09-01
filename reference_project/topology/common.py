"""Topology vocabulary shared across node packages.

Templates contribute property slots and annotations to every declaration that
mixes them in, and never reach the blueprint themselves. Categories are the
graph-visible parents: they own a shared property, appear in the hierarchy, and
let an edge declare its endpoint as a whole category rather than one component.
"""

from dataclasses import dataclass

from kg_build_system import (
    AbstractEdge, AbstractNode, Annotation, EdgeLabel, EdgeOptions,
    EdgeOptionsTemplate, EdgeTemplate, NodeLabel, NodeOptions,
    NodeOptionsTemplate, NodeTemplate, PropertySlot, property,
)


@dataclass(frozen=True)
class Provenance(Annotation):
    """Records which build stage produced or tracks a component."""

    namespace = "reference_project"
    annotation_id = "provenance"

    stage: str


class ProvenancedNodeTemplate(NodeTemplate):
    """Every node records the feed version that produced it."""

    options = NodeOptionsTemplate(annotations=(Provenance(stage="built"),))
    source_version: PropertySlot[str] = property()
    """The data release the node's facts were built from."""


class DocumentedAbstractNode(AbstractNode):
    """Category: every documented entity carries a human-readable summary."""

    options = NodeOptions(annotations=(NodeLabel("Documented"),))
    summary: PropertySlot[str] = property()
    """A one-line human-readable rendering of the entity."""


class RecordedRelationEdgeTemplate(EdgeTemplate):
    """Every relation states what it is asserted as at, and by which stage."""

    options = EdgeOptionsTemplate(annotations=(Provenance(stage="derived"),))
    as_at: PropertySlot[str] = property()
    """The date or period the relation is asserted as at."""

    stage: PropertySlot[str] = property()
    """The build stage that asserted the relation."""


class MonitoredRelationAbstractEdge(AbstractEdge[DocumentedAbstractNode, DocumentedAbstractNode]):
    """Category: a relationship asserted by the monitored estate data."""

    options = EdgeOptions(annotations=(EdgeLabel("MONITORED"),))
