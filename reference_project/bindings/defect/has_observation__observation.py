from kg_build_system import edge_binding

from reference_project.bindings.common import relation_stamps
from reference_project.table.projections.observations import ObservationProjection
from reference_project.topology.defect.has_observation__observation import HasObservationEdge


# Both endpoints and the relation itself are named by identifiers the survey
# failed to record on some rows; those rows are dropped, since default_to on a
# key would assert relations between entities that were never distinguished.
has_observation_binding = edge_binding(
    target=HasObservationEdge,
    build_key=ObservationProjection.observation_uid.where_present(),
    source_build_key=ObservationProjection.defect_id.where_present(),
    target_build_key=ObservationProjection.observation_uid.where_present(),
    properties=HasObservationEdge(
        as_at=ObservationProjection.observed_on.default_to("Undated"),
        **relation_stamps,
    ),
)
