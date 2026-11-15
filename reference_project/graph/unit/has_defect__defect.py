"""Unit -[:HAS_DEFECT]-> Defect, from the surveyed element grain."""

from kg_build_system import (
    Claim, Edge, EdgeLabel, EdgeOptions, Limitation, Meaning, Purpose,
)

from reference_project.graph.common import (
    MonitoredRelationAbstractEdge, RecordedRelationEdgeTemplate,
)
from reference_project.graph.defect import DefectNode
from reference_project.graph.unit import UnitNode


class HasDefectEdge(
    RecordedRelationEdgeTemplate, MonitoredRelationAbstractEdge, Edge[UnitNode, DefectNode]
):
    """Relates equipment to a defect recorded against it."""

    options = EdgeOptions(
        annotations=(EdgeLabel("HAS_DEFECT"),),
        meaning=Meaning(
            purpose=Purpose(
                "Find the defects a survey reported against one unit.",
                limitations=(
                    Limitation(
                        "A defect whose unit reference resolves to no registered unit is absent."
                    ),
                ),
            ),
            claims=(
                Claim("The edge runs from the unit to the defect."),
            ),
        ),
    )
