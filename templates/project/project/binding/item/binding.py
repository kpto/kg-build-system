"""Bind the fixture item rows to the item record."""

from kg_build_system import (
    BindingOptions,
    Claim,
    Limitation,
    Meaning,
    NodeValues,
    Purpose,
    node_binding,
)

from project.graph.item.node import ItemNode
from project.relation.source.items import Items


item_binding = node_binding(
    target=ItemNode,
    rows=Items.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.item_id.alter_rows().drop_null(),
        properties=ItemNode(label=row.item_label.default_to("Untitled item")),
    ),
    debug_name="fixture_item",
    options=BindingOptions(
        meaning=Meaning(
            purpose=Purpose(
                "The items relation fulfils the ITEM use as one item record per "
                "fixture row: each row supplies one node, keyed by the item id, "
                "covering every item in the fixture source.",
                limitations=(
                    Limitation(
                        "A conformance fixture; replace it with the project's binding."
                    ),
                ),
            ),
            claims=(
                Claim("One fixture item row produces one item node."),
            ),
        ),
    ),
)
