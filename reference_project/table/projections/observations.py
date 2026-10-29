"""The observation grain: monitoring records sit one level below a defect.

Expanding ``observations`` changes the row count again, so it cannot live in the
defect projection, which has one row plan. This projection consumes that one and
carries the defect key through so the relation back to it can be bound.
"""

from kg_build_system import Projection, projection_field

from reference_project.table.projections.defects import DefectProjection

observation = DefectProjection.observations.expand()


class ObservationProjection(Projection(DefectProjection.row_source())):
    """One row per observation taken against a defect."""

    defect_id = projection_field(DefectProjection.defect_id)
    observation_uid = projection_field(observation.pick(lambda value: value.observation_uid))
    value = projection_field(observation.pick(lambda value: value.value))
    observed_by = projection_field(observation.pick(lambda value: value.observed_by))
    observed_on = projection_field(observation.pick(lambda value: value.observed_on))
