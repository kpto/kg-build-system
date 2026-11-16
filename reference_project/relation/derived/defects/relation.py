"""The defect relation: one row per defect the survey documents report."""

from kg_build_system import (
    Claim,
    Contract,
    Definition,
    DerivedRelation,
    DerivedRelationOptions,
    FieldDefinition,
    Limitation,
    Meaning,
    Omitted,
    Purpose,
    computed_field,
)

from reference_project.relation.derived.defects._unnest import DefectRows

defect_rows = DefectRows.row_source()


class Defects(DerivedRelation(defect_rows)):
    """One row per defect nested in one survey document."""

    options = DerivedRelationOptions(
        name="defects",
        contract=Contract(
            definition=Definition(
                grain="one row per defect nested in one survey document",
                identity=("survey_id", "defect_id"),
            ),
            meaning=Meaning(
                purpose=Purpose(
                    "Read every defect the surveys reported, with the unit and the "
                    "visit it belongs to.",
                    limitations=(
                        Limitation(
                            "A defect is repeated once per survey document that reports "
                            "it; the same physical defect across visits appears as "
                            "separate rows."
                        ),
                        Limitation(
                            "The row keeps the survey's unit reference; a reference "
                            "that resolves to no registered unit is not repaired here."
                        ),
                    ),
                ),
                claims=(
                    Claim("One row is one defect nested in one survey document."),
                    Claim("The row carries the survey's site and timestamp unchanged."),
                ),
            ),
        ),
    )

    survey_id = computed_field(
        defect_rows.shape.survey_id,
        definition=FieldDefinition("The survey document the defect was reported in."),
        meaning=Omitted,
    )
    surveyed_on = computed_field(
        defect_rows.shape.surveyed_on,
        definition=FieldDefinition(
            "The timestamp of that survey document.",
            null_meaning="The document records no timestamp.",
        ),
        meaning=Omitted,
    )
    unit_ref = computed_field(
        defect_rows.shape.unit_ref,
        definition=FieldDefinition(
            "The register unit reference the survey recorded for the defect's element.",
            null_meaning="The element names no unit.",
        ),
        meaning=Omitted,
    )
    defect_id = computed_field(
        defect_rows.shape.defect_id,
        definition=FieldDefinition("The defect identifier within the survey document."),
        meaning=Omitted,
    )
    title = computed_field(
        defect_rows.shape.title,
        definition=FieldDefinition(
            "The surveyor's description of the defect.",
            null_meaning="The surveyor wrote no title.",
        ),
        meaning=Omitted,
    )
    condition_rating = computed_field(
        defect_rows.shape.condition_rating,
        definition=FieldDefinition(
            "The condition rating on the survey's own scale.",
            null_meaning="The surveyor left the rating blank.",
        ),
        meaning=Omitted,
    )
    observed_on = computed_field(
        defect_rows.shape.observed_on,
        definition=FieldDefinition(
            "The date the defect was observed.",
            null_meaning="The surveyor recorded no date.",
        ),
        meaning=Omitted,
    )
    observations = computed_field(
        defect_rows.shape.observations,
        definition=FieldDefinition(
            "The observations nested under the defect, carried for the next grain."
        ),
        meaning=Omitted,
    )
