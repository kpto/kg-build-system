from kg_build_system import edge_binding

from reference_project.bindings.common import relation_stamps
from reference_project.table.surveys import SurveysTable
from reference_project.topology.survey.surveyed_at__site import SurveyedAtEdge


surveyed_at_binding = edge_binding(
    target=SurveyedAtEdge,
    build_key=SurveysTable.survey_id.where_present(),
    source_build_key=SurveysTable.survey_id.where_present(),
    target_build_key=SurveysTable.site_id.where_present(),
    properties=SurveyedAtEdge(
        as_at=SurveysTable.surveyed_on,
        **relation_stamps,
    ),
)
