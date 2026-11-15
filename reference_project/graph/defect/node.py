from kg_build_system import (
    Claim, Limitation, Meaning, Node, NodeLabel, NodeOptions, PropertySlot,
    Purpose, property,
)

from reference_project.graph.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)


class DefectNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """A defect recorded against an element during a survey."""

    options = NodeOptions(
        annotations=(NodeLabel("Defect"),),
        meaning=Meaning(
            purpose=Purpose(
                "Read the condition a survey reported for one element of a unit.",
                limitations=(
                    Limitation(
                        "A defect is a surveyor's finding; it is not a confirmed failure, a repair obligation or a cost."
                    ),
                    Limitation(
                        "The condition rating is the survey's own scale; two surveys need not share it."
                    ),
                ),
            ),
            claims=(
                Claim("The defect is identified within the survey document that reports it."),
            ),
        ),
    )

    title: PropertySlot[str] = property(
        meaning=Meaning(
            claims=(Claim("The surveyor's one-line description of the defect."),),
        ),
    )

    condition_rating: PropertySlot[str] = property(
        meaning=Meaning(
            claims=(Claim("The condition rating the survey assigned, on the survey's own scale."),),
        ),
    )
