from kg_build_system import (
    Claim, Limitation, Meaning, Node, NodeLabel, NodeOptions, PropertySlot,
    Purpose, property,
)

from reference_project.graph.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)


class ObservationNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """One measurement taken while monitoring a defect."""

    options = NodeOptions(
        annotations=(NodeLabel("Observation"),),
        meaning=Meaning(
            purpose=Purpose(
                "Read one monitoring record taken against a defect.",
                limitations=(
                    Limitation(
                        "An observation is one record at one time; it is not a trend."
                    ),
                    Limitation(
                        "The value is the surveyor's reading; the graph applies no calibration."
                    ),
                ),
            ),
            claims=(
                Claim("The observation is identified by its observation identifier within the survey document."),
            ),
        ),
    )

    value: PropertySlot[float] = property(
        meaning=Meaning(
            claims=(Claim("The recorded value in the unit the surveyor used."),),
        ),
    )

    method: PropertySlot[str] = property(
        meaning=Meaning(
            claims=(Claim("The method or instrument the surveyor recorded."),),
        ),
    )

    observed_on: PropertySlot[str] = property(
        meaning=Meaning(
            claims=(Claim("The date the observation was recorded."),),
        ),
    )
