"""Expand each item row to one row per nested part."""

from kg_build_system import Definition, Stage, StageOptions, computed_field

from project.relation.source.items import Items

part = Items.parts.alter_rows().expand()


class PartRows(Stage(Items.row_source())):

    options = StageOptions(
        name="part_rows",
        definition=Definition(
            grain="one row per part nested in one item",
            identity=("item_id", "part_id"),
        ),
    )

    item_id = computed_field(Items.item_id.alter_rows().drop_null())
    part_id = computed_field(
        part.extract(lambda item: item.part_id).alter_rows().drop_null()
    )
    part_value = computed_field(part.extract(lambda item: item.value))
