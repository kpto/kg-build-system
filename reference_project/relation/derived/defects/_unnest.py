"""Flatten a survey document to one row per nested defect.

The document nests areas, then elements, then defects, so reaching a defect
takes three correlated expansions in one row plan. The stage keeps the grain
private; the published relation is ``Defects``.
"""

from kg_build_system import Definition, Stage, StageOptions, computed_field

from reference_project.relation.source.estate.surveys import SurveysSourceRelation

area = SurveysSourceRelation.areas.alter_rows().expand()
element = area.extract(lambda value: value.elements).alter_rows().expand()
defect = element.extract(lambda value: value.defects).alter_rows().expand()


class DefectRows(Stage(SurveysSourceRelation.row_source())):
    """One row per defect nested in one survey document."""

    options = StageOptions(
        name="defect_rows",
        definition=Definition(
            grain="one row per defect nested in one survey document",
            identity=("survey_id", "defect_id"),
        ),
    )

    survey_id = computed_field(SurveysSourceRelation.survey_id.alter_rows().drop_null())
    surveyed_on = computed_field(SurveysSourceRelation.surveyed_on)
    unit_ref = computed_field(element.extract(lambda value: value.unit_ref))
    defect_id = computed_field(defect.extract(lambda value: value.defect_id))
    title = computed_field(defect.extract(lambda value: value.title))
    condition_rating = computed_field(
        defect.extract(lambda value: value.condition_rating)
    )
    observed_on = computed_field(defect.extract(lambda value: value.observed_on))
    observations = computed_field(defect.extract(lambda value: value.observations))
