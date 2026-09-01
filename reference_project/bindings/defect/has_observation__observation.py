from kg_build_system import edge_binding

from reference_project.bindings.common import relation_stamps
from reference_project.table.projections.observations import ObservationProjection
from reference_project.topology.defect.has_observation__observation import HasObservationEdge


has_observation_binding = edge_binding(
    target=HasObservationEdge,
    build_key=ObservationProjection.observation_uid,
    source_build_key=ObservationProjection.defect_id,
    target_build_key=ObservationProjection.observation_uid,
    properties=HasObservationEdge(
        as_at=ObservationProjection.observed_on,
        **relation_stamps,
    ),
)
