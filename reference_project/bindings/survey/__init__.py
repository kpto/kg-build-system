from kg_build_system import node_binding

from reference_project.bindings.common import provenance_stamps
from reference_project.table.surveys import SurveysTable
from reference_project.topology.survey import SurveyVisitNode


# The survey document's own grain is one row per visit, so the visit binds
# directly off the contract even though deeper grains need projections.
survey_visit_binding = node_binding(
    target=SurveyVisitNode,
    build_key=SurveysTable.survey_id.where_present(),
    properties=SurveyVisitNode(
        surveyed_on=SurveysTable.surveyed_on.default_to("Undated survey"),
        surveyor=SurveysTable.surveyor.pick(lambda value: value.name).default_to("Unattributed"),
        practice=(
            SurveysTable.surveyor
            .pick(lambda value: value.firm)
            .pick(lambda value: value.name)
        ),
        summary=SurveysTable.survey_id.default_to("Unidentified survey"),
        **provenance_stamps,
    ),
)
