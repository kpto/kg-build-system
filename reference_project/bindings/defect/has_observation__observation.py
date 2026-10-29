from kg_build_system import EdgeValues, edge_binding

from reference_project.bindings.common import relation_stamps
from reference_project.table.projections.observations import ObservationProjection
from reference_project.topology.defect.has_observation__observation import HasObservationEdge


# Both endpoints and the relation itself are named by identifiers the survey
# failed to record on some rows; those rows are dropped, since default_to on a
# key would assert relations between entities that were never distinguished.
has_observation_binding = edge_binding(
    target=HasObservationEdge,
    rows=ObservationProjection.row_source(),
    bind=lambda row: EdgeValues(
        build_key=row.observation_uid.alter_rows().drop_null(),
        source_build_key=row.defect_id.alter_rows().drop_null(),
        target_build_key=row.observation_uid.alter_rows().drop_null(),
        properties=HasObservationEdge(
            as_at=row.observed_on.default_to("Undated"),
            **relation_stamps,
        ),
    ),
)
