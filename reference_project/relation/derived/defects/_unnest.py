"""Flatten a survey document to one row per nested defect.

The document nests areas, then elements, then defects, so reaching a defect
takes three correlated expansions in one row plan. The stage keeps the grain
private; the published relation is ``Defects``.
"""

from kg_build_system import (
    Definition,
    Omitted,
    Stage,
    StageOptions,
    computed_field,
)

from reference_project.relation.source.estate.surveys import SurveysSourceRelation

survey_rows = SurveysSourceRelation.row_source()
area = survey_rows.shape.areas.alter_rows().expand()
element = area.extract(lambda value: value.elements).alter_rows().expand()
defect = element.extract(lambda value: value.defects).alter_rows().expand()


class DefectRows(Stage(survey_rows)):
    """One row per defect nested in one survey document."""

    options = StageOptions(
        name="defect_rows",
        definition=Definition(
            grain="one row per defect nested in one survey document",
            identity=("survey_id", "defect_id"),
        ),
    )

    survey_id = computed_field(
        survey_rows.shape.survey_id.alter_rows().drop_null(), meaning=Omitted
    )
    surveyed_on = computed_field(survey_rows.shape.surveyed_on, meaning=Omitted)
    unit_ref = computed_field(
        element.extract(lambda value: value.unit_ref), meaning=Omitted
    )
    defect_id = computed_field(
        defect.extract(lambda value: value.defect_id), meaning=Omitted
    )
    title = computed_field(defect.extract(lambda value: value.title), meaning=Omitted)
    condition_rating = computed_field(
        defect.extract(lambda value: value.condition_rating),
        meaning=Omitted,
    )
    observed_on = computed_field(
        defect.extract(lambda value: value.observed_on), meaning=Omitted
    )
    observations = computed_field(
        defect.extract(lambda value: value.observations), meaning=Omitted
    )
