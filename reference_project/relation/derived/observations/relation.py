"""The observation relation: one row per observation the surveys recorded."""

from kg_build_system import (
    Claim,
    Contract,
    Definition,
    DerivedRelation,
    DerivedRelationOptions,
    FieldDefinition,
    Limitation,
    Meaning,
    Purpose,
    computed_field,
)

from reference_project.relation.derived.observations._unnest import ObservationRows

observation_rows = ObservationRows.row_source()


class Observations(DerivedRelation(observation_rows)):
    """One row per observation nested in one defect."""

    options = DerivedRelationOptions(
        name="observations",
        contract=Contract(
            definition=Definition(
                grain="one row per observation nested in one defect",
                identity=("survey_id", "defect_id", "observation_uid"),
            ),
            meaning=Meaning(
                purpose=Purpose(
                    "Read one monitoring record per defect, with the keys that place "
                    "it in its survey and defect.",
                    limitations=(
                        Limitation(
                            "An observation is present only when the survey document "
                            "nested it under a defect."
                        ),
                        Limitation(
                            "The observation inherits its date and value text from the "
                            "document; the graph parses neither."
                        ),
                    ),
                ),
                claims=(Claim("One row is one observation of one defect."),),
            ),
        ),
    )

    survey_id = computed_field(
        observation_rows.shape.survey_id,
        definition=FieldDefinition(
            "The survey document the observation was recorded in."
        ),
    )
    defect_id = computed_field(
        observation_rows.shape.defect_id,
        definition=FieldDefinition(
            "The defect identifier the observation belongs to."
        ),
    )
    observation_uid = computed_field(
        observation_rows.shape.observation_uid,
        definition=FieldDefinition(
            "The observation identifier within the survey document."
        ),
    )
    value = computed_field(
        observation_rows.shape.value,
        definition=FieldDefinition(
            "The recorded value in the surveyor's unit."
        ),
    )
    observed_by = computed_field(
        observation_rows.shape.observed_by,
        definition=FieldDefinition(
            "The surveyor or instrument that recorded the observation."
        ),
    )
    observed_on = computed_field(
        observation_rows.shape.observed_on,
        definition=FieldDefinition(
            "The date the observation was recorded."
        ),
    )
