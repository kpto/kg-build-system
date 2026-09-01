"""Defect -[:HAS_OBSERVATION]-> Observation, from the monitoring grain."""

from kg_build_system import Edge, EdgeLabel, EdgeOptions

from reference_project.topology.common import (
    MonitoredRelationAbstractEdge, RecordedRelationEdgeTemplate,
)
from reference_project.topology.defect import DefectNode
from reference_project.topology.observation import ObservationNode


class HasObservationEdge(
    RecordedRelationEdgeTemplate, MonitoredRelationAbstractEdge,
    Edge[DefectNode, ObservationNode],
):
    """Relates a defect to one observation taken while monitoring it."""

    options = EdgeOptions(annotations=(EdgeLabel("HAS_OBSERVATION"),))
