from kg_build_system import (
    BindingOptions, EdgeValues, Limitation, Meaning, Purpose, edge_binding,
)

from reference_project.binding.common import relation_stamps
from reference_project.relation.derived.observations.relation import Observations
from reference_project.graph.defect.has_observation__observation import HasObservationEdge


# Both endpoints and the relation itself are named by identifiers the survey
# failed to record on some rows; those rows are dropped, since default_to on a
# key would assert relations between entities that were never distinguished.
has_observation_binding = edge_binding(
    target=HasObservationEdge,
    rows=Observations.row_source(),
    bind=lambda row: EdgeValues(
        build_key=row.observation_uid.alter_rows().drop_null(),
        source_build_key=row.defect_id.alter_rows().drop_null(),
        target_build_key=row.observation_uid.alter_rows().drop_null(),
        properties=HasObservationEdge(
            as_at=row.observed_on.default_to("Undated"),
            **relation_stamps,
        ),
    ),
    options=BindingOptions(
        meaning=Meaning(
            purpose=Purpose(
                "Fulfil HasObservationEdge from the Observations relation: each observation names its defect and its own identifier.",
                limitations=(
            Limitation(
                "An observation whose identifier or defect identifier is absent is excluded."
            ),
                ),
            ),
        ),
    ),
)
