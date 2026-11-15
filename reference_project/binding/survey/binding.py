from kg_build_system import (
    BindingOptions, Limitation, Meaning, NodeValues, Purpose, node_binding,
)

from reference_project.binding.common import provenance_stamps
from reference_project.relation.source.estate.surveys import SurveysSourceRelation
from reference_project.graph.survey import SurveyVisitNode


# The survey document's own grain is one row per visit, so the visit binds
# directly off the contract even though deeper grains need projections.
survey_visit_binding = node_binding(
    target=SurveyVisitNode,
    rows=SurveysSourceRelation.row_source(),
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
    options=BindingOptions(
        meaning=Meaning(
            purpose=Purpose(
                "Fulfil SurveyVisitNode from the survey documents: one document gives one visit.",
                limitations=(
            Limitation(
                "The practice is present only when the document names one."
            ),
                ),
            ),
        ),
    ),
)
