from kg_build_system import EdgeValues, edge_binding

from reference_project.bindings.common import relation_stamps
from reference_project.table.surveys import SurveysTable
from reference_project.topology.survey.surveyed_at__site import SurveyedAtEdge


surveyed_at_binding = edge_binding(
    target=SurveyedAtEdge,
    rows=SurveysTable,
    bind=lambda row: EdgeValues(
        build_key=row.survey_id.alter_rows().drop_null(),
        source_build_key=row.survey_id.alter_rows().drop_null(),
        target_build_key=row.site_id.alter_rows().drop_null(),
        properties=SurveyedAtEdge(
            as_at=row.surveyed_on,
            **relation_stamps,
        ),
    ),
)
