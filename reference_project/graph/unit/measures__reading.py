"""Unit -[:MEASURES]-> Reading, from each telemetry partition."""

from kg_build_system import (
    Claim, Edge, EdgeLabel, EdgeOptions, Limitation, Meaning, Purpose,
)

from reference_project.graph.common import (
    MonitoredRelationAbstractEdge, TimestampedRelationEdgeTemplate,
)
from reference_project.graph.reading import ReadingNode
from reference_project.graph.unit import UnitNode


class MeasuresEdge(
    TimestampedRelationEdgeTemplate, MonitoredRelationAbstractEdge, Edge[UnitNode, ReadingNode]
):
    """Relates equipment to a sample reported against it."""

    options = EdgeOptions(
        annotations=(EdgeLabel("MEASURES"),),
        meaning=Meaning(
            purpose=Purpose(
                "Find the telemetry readings reported for one unit.",
                limitations=(
                    Limitation(
                        "Only readings in the exported logger feeds are present; a unit without a logger has no edge."
                    ),
                ),
            ),
            claims=(
                Claim("The edge runs from the unit to the reading."),
            ),
        ),
    )
