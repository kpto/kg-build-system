"""Site -[:HAS_UNIT]-> Unit, from the equipment register."""

from kg_build_system import (
    Claim, Edge, EdgeLabel, EdgeOptions, Limitation, Meaning, Purpose,
)

from reference_project.graph.common import (
    MonitoredRelationAbstractEdge, RecordedRelationEdgeTemplate,
)
from reference_project.graph.site import SiteNode
from reference_project.graph.unit import UnitNode


class HasUnitEdge(
    RecordedRelationEdgeTemplate, MonitoredRelationAbstractEdge, Edge[SiteNode, UnitNode]
):
    """Relates a site to equipment installed at it."""

    options = EdgeOptions(
        annotations=(EdgeLabel("HAS_UNIT"),),
        meaning=Meaning(
            purpose=Purpose(
                "Find the equipment installed at one site.",
                limitations=(
                    Limitation(
                        "Installation is asserted as at the register release; a move or removal after the release is absent."
                    ),
                ),
            ),
            claims=(
                Claim("The edge runs from the site to the unit."),
            ),
        ),
    )
