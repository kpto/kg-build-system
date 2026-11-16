"""The fixture source relation: one row per item, with its nested parts."""

from kg_build_system import (
    Array,
    Claim,
    Contract,
    Definition,
    Field,
    FieldDefinition,
    Limitation,
    Meaning,
    Omitted,
    Purpose,
    SourceRelation,
    SourceRelationOptions,
    Struct,
    field,
)

from project.asset.fixture import Fixture


class Part(Struct):
    part_id: Field[str] = field(
        definition=FieldDefinition("The fixture's part identifier."),
        meaning=Omitted,
    )
    value: Field[float] = field(
        definition=FieldDefinition("The fixture's part value."),
        meaning=Omitted,
    )


class Items(SourceRelation[Fixture]):
    options = SourceRelationOptions(
        name="items",
        contract=Contract(
            definition=Definition(
                grain="one row per item in the fixture source",
                identity=("item_id",),
            ),
            meaning=Meaning(
                purpose=Purpose(
                    "Read the fixture items and their nested parts.",
                    limitations=(
                        Limitation(
                            "A conformance fixture; replace it with the project's "
                            "source relation."
                        ),
                    ),
                ),
                claims=(Claim("The fixture source holds one item per row."),),
            ),
        ),
    )

    item_id: Field[str] = field(
        definition=FieldDefinition("The fixture's item identifier."),
        meaning=Omitted,
    )
    item_label: Field[str] = field(
        definition=FieldDefinition("The fixture's item label."),
        meaning=Omitted,
    )
    parts: Field[Array[Part]] = field(
        definition=FieldDefinition("The parts nested under the item."),
        meaning=Omitted,
    )
