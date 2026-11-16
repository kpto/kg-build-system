"""Expand each item row to one row per nested part."""

from kg_build_system import Definition, Stage, StageOptions, computed_field

from project.relation.source.items import Items

items = Items.row_source()


class PartRows(Stage(items)):

    options = StageOptions(
        name="part_rows",
        definition=Definition(
            grain="one row per part nested in one item",
            identity=("item_id", "part_id"),
        ),
    )

    item_id = computed_field(items.shape.item_id.alter_rows().drop_null())
    part_id = computed_field(
        items.shape.parts.alter_rows()
        .expand()
        .extract(lambda item: item.part_id)
        .alter_rows()
        .drop_null()
    )
    part_value = computed_field(
        items.shape.parts.alter_rows().expand().extract(lambda item: item.value)
    )
