"""Defect -[:HAS_OBSERVATION]-> Observation, from the monitoring grain."""

from kg_build_system import (
    Claim, Edge, EdgeLabel, EdgeOptions, Limitation, Meaning, Purpose,
)

from reference_project.graph.common import (
    MonitoredRelationAbstractEdge, RecordedRelationEdgeTemplate,
)
from reference_project.graph.defect import DefectNode
from reference_project.graph.observation import ObservationNode


class HasObservationEdge(
    RecordedRelationEdgeTemplate, MonitoredRelationAbstractEdge,
    Edge[DefectNode, ObservationNode],
):
    """Relates a defect to one observation taken while monitoring it."""

    options = EdgeOptions(
        annotations=(EdgeLabel("HAS_OBSERVATION"),),
        meaning=Meaning(
            purpose=Purpose(
                "Find the observations recorded for one defect.",
                limitations=(
                    Limitation(
                        "Only observations nested in the survey document are present."
                    ),
                ),
            ),
            claims=(
                Claim("The edge runs from the defect to the observation."),
            ),
        ),
    )
