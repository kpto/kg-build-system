from kg_build_system import (
    BindingOptions, EdgeValues, Limitation, Meaning, Purpose, edge_binding,
)

from reference_project.binding.common import relation_stamps
from reference_project.relation.source.estate.surveys import SurveysSourceRelation
from reference_project.graph.survey.surveyed_at__site import SurveyedAtEdge


surveyed_at_binding = edge_binding(
    target=SurveyedAtEdge,
    rows=SurveysSourceRelation.row_source(),
    bind=lambda row: EdgeValues(
        build_key=row.survey_id.alter_rows().drop_null(),
        source_build_key=row.survey_id.alter_rows().drop_null(),
        target_build_key=row.site_id.alter_rows().drop_null(),
        properties=SurveyedAtEdge(
            as_at=row.surveyed_on,
            **relation_stamps,
        ),
    ),
    options=BindingOptions(
        meaning=Meaning(
            purpose=Purpose(
                "Fulfil SurveyedAtEdge from the survey documents: each document names its own identifier and the site it was carried out at.",
                limitations=(
            Limitation(
                "A document whose site identifier is absent is excluded."
            ),
                ),
            ),
        ),
    ),
)
