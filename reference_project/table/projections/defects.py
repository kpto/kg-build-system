"""The defect grain: flattening the survey document to one row per defect.

The document nests areas, then elements, then defects, so reaching a defect
takes three correlated expansions in one row plan. It is published because four
bindings need this grain: the defect node, the two relations hanging off it, and
the observation grain built on top.
"""

from kg_build_system import Projection, computed_field

from reference_project.table.surveys import SurveysTable

area = SurveysTable.areas.alter_rows().expand()
element = area.extract(lambda value: value.elements).alter_rows().expand()
defect = element.extract(lambda value: value.defects).alter_rows().expand()


class DefectProjection(Projection(SurveysTable.row_source())):
    """One row per defect, with the element and visit it came from."""

    survey_id = computed_field(SurveysTable.survey_id.alter_rows().drop_null())
    surveyed_on = computed_field(SurveysTable.surveyed_on)
    unit_ref = computed_field(element.extract(lambda value: value.unit_ref))
    defect_id = computed_field(defect.extract(lambda value: value.defect_id))
    title = computed_field(defect.extract(lambda value: value.title))
    condition_rating = computed_field(defect.extract(lambda value: value.condition_rating))
    observed_on = computed_field(defect.extract(lambda value: value.observed_on))
    observations = computed_field(defect.extract(lambda value: value.observations))
