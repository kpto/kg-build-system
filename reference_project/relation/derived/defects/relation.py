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
    Purpose,
    computed_field,
)

from reference_project.relation.derived.defects._unnest import DefectRows


class Defects(DerivedRelation(DefectRows.row_source())):
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
        DefectRows.survey_id,
        definition=FieldDefinition("The survey document the defect was reported in."),
    )
    surveyed_on = computed_field(
        DefectRows.surveyed_on,
        definition=FieldDefinition(
            "The timestamp of that survey document.",
            null_meaning="The document records no timestamp.",
        ),
    )
    unit_ref = computed_field(
        DefectRows.unit_ref,
        definition=FieldDefinition(
            "The register unit reference the survey recorded for the defect's element.",
            null_meaning="The element names no unit.",
        ),
    )
    defect_id = computed_field(
        DefectRows.defect_id,
        definition=FieldDefinition(
            "The defect identifier within the survey document."
        ),
    )
    title = computed_field(
        DefectRows.title,
        definition=FieldDefinition(
            "The surveyor's description of the defect.",
            null_meaning="The surveyor wrote no title.",
        ),
    )
    condition_rating = computed_field(
        DefectRows.condition_rating,
        definition=FieldDefinition(
            "The condition rating on the survey's own scale.",
            null_meaning="The surveyor left the rating blank.",
        ),
    )
    observed_on = computed_field(
        DefectRows.observed_on,
        definition=FieldDefinition(
            "The date the defect was observed.",
            null_meaning="The surveyor recorded no date.",
        ),
    )
    observations = computed_field(
        DefectRows.observations,
        definition=FieldDefinition(
            "The observations nested under the defect, carried for the next grain."
        ),
    )
