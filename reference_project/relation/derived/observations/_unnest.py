"""Expand the observations nested under each defect row."""

from kg_build_system import Definition, Stage, StageOptions, computed_field

from reference_project.relation.derived.defects.relation import Defects

defect_rows = Defects.row_source()

observation = defect_rows.shape.observations.alter_rows().expand()


class ObservationRows(Stage(defect_rows)):
    """One row per observation nested in one defect."""

    options = StageOptions(
        name="observation_rows",
        definition=Definition(
            grain="one row per observation nested in one defect",
            identity=("survey_id", "defect_id", "observation_uid"),
        ),
    )

    survey_id = computed_field(defect_rows.shape.survey_id)
    defect_id = computed_field(defect_rows.shape.defect_id)
    observation_uid = computed_field(
        observation.extract(lambda value: value.observation_uid)
    )
    value = computed_field(observation.extract(lambda value: value.value))
    observed_by = computed_field(observation.extract(lambda value: value.observed_by))
    observed_on = computed_field(observation.extract(lambda value: value.observed_on))
