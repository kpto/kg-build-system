from kg_build_system import (
    Claim, Limitation, Meaning, Node, NodeLabel, NodeOptions, PropertySlot,
    Purpose, property,
)

from reference_project.graph.common import (
    DocumentedAbstractNode, ProvenancedNodeTemplate,
)


class SiteNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    """A monitored site: a premises the estate maintains."""

    options = NodeOptions(
        annotations=(NodeLabel("Site"),),
        meaning=Meaning(
            purpose=Purpose(
                "Group the equipment and surveys that belong to one premises.",
                limitations=(
                    Limitation(
                        "A site is a register entry, not a surveyed condition or a legal property boundary."
                    ),
                ),
            ),
            claims=(
                Claim("The site is identified by the register's site identifier."),
            ),
        ),
    )

    name: PropertySlot[str] = property(
        meaning=Meaning(
            claims=(Claim("The site's display name as the register spells it."),),
        ),
    )

    city: PropertySlot[str] = property(
        meaning=Meaning(
            claims=(Claim("The city of the site's contact address in the register."),),
        ),
    )
