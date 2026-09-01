"""The defect grain: flattening the survey document to one row per defect.

The document nests areas, then elements, then defects, so reaching a defect
takes three correlated expansions in one row plan. It is published because four
bindings need this grain: the defect node, the two relations hanging off it, and
the observation grain built on top.
"""

from kg_build_system import Projection, projection_field

from reference_project.table.surveys import SurveysTable

area = SurveysTable.areas.expand()
element = area.pick(lambda value: value.elements).expand()
defect = element.pick(lambda value: value.defects).expand()


class DefectProjection(Projection):
    """One row per defect, with the element and visit it came from."""

    survey_id = projection_field(SurveysTable.survey_id.where_present())
    surveyed_on = projection_field(SurveysTable.surveyed_on)
    unit_ref = projection_field(element.pick(lambda value: value.unit_ref))
    defect_id = projection_field(defect.pick(lambda value: value.defect_id))
    title = projection_field(defect.pick(lambda value: value.title))
    condition_rating = projection_field(defect.pick(lambda value: value.condition_rating))
    observed_on = projection_field(defect.pick(lambda value: value.observed_on))
    observations = projection_field(defect.pick(lambda value: value.observations))
