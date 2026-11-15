"""Bind the fixture part rows to the part record."""

from kg_build_system import (
    BindingOptions,
    Claim,
    Limitation,
    Meaning,
    NodeValues,
    Purpose,
    node_binding,
)

from project.graph.part.node import PartNode
from project.relation.derived.item_parts.relation import ItemParts


part_binding = node_binding(
    target=PartNode,
    rows=ItemParts.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.item_id.append("::").append(row.part_id),
        properties=PartNode(value=row.part_value),
    ),
    debug_name="fixture_part",
    options=BindingOptions(
        meaning=Meaning(
            purpose=Purpose(
                "The item_parts relation fulfils the PART use as one part record per "
                "item-part row: each row supplies one node, keyed by the item and "
                "part ids, covering every part the fixture source nests.",
                limitations=(
                    Limitation(
                        "A conformance fixture; replace it with the project's binding."
                    ),
                ),
            ),
            claims=(
                Claim("One item-part row produces one part node."),
            ),
        ),
    ),
)
