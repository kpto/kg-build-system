from kg_build_system import (
    Claim, Limitation, Meaning, Node, NodeLabel, NodeOptions, PropertySlot,
    Purpose, property,
)
from kg_build_system import Timestamp

from reference_project.graph.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)


class ReadingNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """One measurement sample reported by a logger against a unit."""

    options = NodeOptions(
        annotations=(NodeLabel("Reading"),),
        meaning=Meaning(
            purpose=Purpose(
                "Compare one telemetry sample with the unit it measures.",
                limitations=(
                    Limitation(
                        "A reading is a logger sample; sensor calibration and logger faults are not represented."
                    ),
                ),
            ),
            claims=(
                Claim("The reading is identified by the feed's reading identifier."),
            ),
        ),
    )

    value: PropertySlot[float | None] = property(
        meaning=Meaning(
            claims=(Claim("The sample value as the logger reported it."),),
        ),
    )

    unit_of_measure: PropertySlot[str] = property(
        meaning=Meaning(
            claims=(Claim("The unit the logger reported the value in."),),
        ),
    )

    recorded_on: PropertySlot[Timestamp | None] = property(
        meaning=Meaning(
            claims=(Claim("The instant the logger recorded the sample."),),
        ),
    )
