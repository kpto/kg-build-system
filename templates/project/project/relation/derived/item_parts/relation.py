"""The published item-part relation."""

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

from project.relation.derived.item_parts._parts import PartRows


class ItemParts(DerivedRelation(PartRows.row_source())):
    """One row per item and part."""

    options = DerivedRelationOptions(
        name="item_parts",
        contract=Contract(
            definition=Definition(
                grain="one row per item and part",
                identity=("item_id", "part_id"),
            ),
            meaning=Meaning(
                purpose=Purpose(
                    "Read the parts of each fixture item as their own relation.",
                    limitations=(
                        Limitation(
                            "A conformance fixture; replace it with the project's "
                            "derived relation."
                        ),
                        Limitation(
                            "An item with no nested part contributes no row here."
                        ),
                    ),
                ),
                claims=(
                    Claim("One row is one part nested in one item."),
                ),
            ),
        ),
    )

    item_id = computed_field(
        PartRows.item_id,
        definition=FieldDefinition("The item identifier the part belongs to."),
    )
    part_id = computed_field(
        PartRows.part_id,
        definition=FieldDefinition("The fixture's part identifier."),
    )
    part_value = computed_field(
        PartRows.part_value,
        definition=FieldDefinition("The fixture's part value."),
    )
