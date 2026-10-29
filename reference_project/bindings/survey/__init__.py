from kg_build_system import NodeValues, node_binding

from reference_project.bindings.common import provenance_stamps
from reference_project.table.surveys import SurveysTable
from reference_project.topology.survey import SurveyVisitNode


# The survey document's own grain is one row per visit, so the visit binds
# directly off the contract even though deeper grains need projections.
survey_visit_binding = node_binding(
    target=SurveyVisitNode,
    rows=SurveysTable,
    bind=lambda row: NodeValues(
        build_key=row.survey_id.alter_rows().drop_null(),
        properties=SurveyVisitNode(
            # A timestamp has no honest sentinel, so an undated survey carries
            # no date at all rather than the text a string property would need.
            surveyed_on=row.surveyed_on,
            surveyor=row.surveyor.extract(lambda value: value.name).default_to("Unattributed"),
            practice=(
                row.surveyor
                .extract(lambda value: value.firm)
                .extract(lambda value: value.name)
            ),
            summary=row.survey_id.default_to("Unidentified survey"),
            **provenance_stamps,
        ),
    ),
)
