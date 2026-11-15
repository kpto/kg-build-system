from kg_build_system import (
    Claim, Limitation, Meaning, Node, NodeLabel, NodeOptions, PropertySlot,
    Purpose, property,
)

from reference_project.graph.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)


class UnitNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """A piece of installed equipment held on the asset register."""

    options = NodeOptions(
        annotations=(NodeLabel("Unit"),),
        meaning=Meaning(
            purpose=Purpose(
                "Identify the equipment a defect or reading is about.",
                limitations=(
                    Limitation(
                        "A unit keeps its reference when it is replaced; the graph does not model the replacement."
                    ),
                ),
            ),
            claims=(
                Claim("The unit is identified by the register's unit reference."),
            ),
        ),
    )

    name: PropertySlot[str] = property(
        meaning=Meaning(
            claims=(Claim("The equipment's display name as the register spells it."),),
        ),
    )

    in_service: PropertySlot[bool] = property(
        meaning=Meaning(
            claims=(Claim("Whether the register lists the unit as in service at the export."),),
        ),
    )

    survey_period: PropertySlot[str] = property(
        meaning=Meaning(
            claims=(Claim("The survey period the register records for the unit."),),
        ),
    )
