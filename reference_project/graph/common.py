"""Graph vocabulary shared across node packages.

Templates contribute property slots and annotations to every declaration that
mixes them in, and never reach the blueprint themselves. Categories are the
graph-visible parents: they own a shared property, appear in the hierarchy, and
let an edge declare its endpoint as a whole category rather than one component.
"""

from dataclasses import dataclass

from kg_build_system import (
    AbstractEdge, AbstractNode, Annotation, Claim, EdgeLabel, EdgeOptions,
    EdgeOptionsTemplate, EdgeTemplate, Meaning, NodeLabel, NodeOptions,
    NodeOptionsTemplate, NodeTemplate, PropertySlot, property,
)
from kg_build_system import Timestamp


@dataclass(frozen=True)
class Provenance(Annotation):
    """Records which build stage produced or tracks a component."""

    namespace = "reference_project"
    annotation_id = "provenance"

    stage: str


class ProvenancedNodeTemplate(NodeTemplate):
    """Every node records the feed version that produced it."""

    options = NodeOptionsTemplate(
        annotations=(Provenance(stage="built"),),
        meaning=Meaning(
            claims=(Claim("Every node records the feed version it was built from."),),
        ),
    )
    source_version: PropertySlot[str] = property(
        meaning=Meaning(
            claims=(Claim("The data release the node's facts were built from."),),
        ),
    )


class DocumentedAbstractNode(AbstractNode):
    """Category: every documented entity carries a human-readable summary."""

    options = NodeOptions(
        annotations=(NodeLabel("Documented"),),
        meaning=Meaning(
            claims=(
                Claim("Every documented record carries a one-line summary for display."),
            ),
        ),
    )
    summary: PropertySlot[str] = property(
        meaning=Meaning(
            claims=(Claim("A one-line human-readable rendering of the record."),),
        ),
    )


class RecordedRelationEdgeTemplate(EdgeTemplate):
    """Every relation states what it is asserted as at, and by which stage."""

    options = EdgeOptionsTemplate(
        annotations=(Provenance(stage="derived"),),
        meaning=Meaning(
            claims=(
                Claim(
                    "Every recorded relation states the stage that asserted it and the "
                    "date it is asserted as at."
                ),
            ),
        ),
    )
    as_at: PropertySlot[str] = property(
        meaning=Meaning(
            claims=(Claim("The date the relation is asserted as at."),),
        ),
    )

    stage: PropertySlot[str] = property(
        meaning=Meaning(
            claims=(Claim("The build stage that asserted the relation."),),
        ),
    )


class TimestampedRelationEdgeTemplate(EdgeTemplate):
    """Every relation states the instant it is asserted as at, and by which stage.

    A sibling of the recorded template rather than a subclass of it: ``as_at``
    is one slot, and a subclass cannot re-declare an inherited slot at another
    type, so a relation whose as-at the feed types as a moment mixes this one.
    """

    options = EdgeOptionsTemplate(
        annotations=(Provenance(stage="derived"),),
        meaning=Meaning(
            claims=(
                Claim(
                    "Every timestamped relation states the instant it is asserted as "
                    "at and the stage that asserted it."
                ),
            ),
        ),
    )
    as_at: PropertySlot[Timestamp | None] = property(
        meaning=Meaning(
            claims=(Claim("The instant the relation is asserted as at."),),
        ),
    )

    stage: PropertySlot[str] = property(
        meaning=Meaning(
            claims=(Claim("The build stage that asserted the relation."),),
        ),
    )


class MonitoredRelationAbstractEdge(AbstractEdge[DocumentedAbstractNode, DocumentedAbstractNode]):
    """Category: a relationship asserted by the monitored estate data."""

    options = EdgeOptions(
        annotations=(EdgeLabel("MONITORED"),),
        meaning=Meaning(
            claims=(
                Claim(
                    "Every monitored relation descends from one category, so a "
                    "consumer can read every relation as one family."
                ),
            ),
        ),
    )
