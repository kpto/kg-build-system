from kg_build_system import node_binding

from reference_project.bindings.common import provenance_stamps
from reference_project.table.projections.observations import ObservationProjection
from reference_project.topology.observation import ObservationNode


observation_binding = node_binding(
    target=ObservationNode,
    build_key=ObservationProjection.observation_uid,
    properties=ObservationNode(
        value=ObservationProjection.value,
        method=ObservationProjection.observed_by,
        observed_on=ObservationProjection.observed_on,
        summary=ObservationProjection.observation_uid,
        **provenance_stamps,
    ),
)
