"""The fixture edge from an item to its part."""

from kg_build_system import (
    Claim,
    Edge,
    EdgeLabel,
    EdgeOptions,
    Limitation,
    Meaning,
    Purpose,
)

from project.graph.item.node import ItemNode
from project.graph.part.node import PartNode


class HasPartEdge(Edge[ItemNode, PartNode]):

    options = EdgeOptions(
        name="item_has_part",
        annotations=(EdgeLabel("HAS_PART"),),
        meaning=Meaning(
            purpose=Purpose(
                "Exercise a relation from a record to a nested record in the "
                "template fixture.",
                limitations=(
                    Limitation(
                        "A conformance fixture; replace it with the project's relation."
                    ),
                ),
            ),
            claims=(Claim("The edge runs from the item to its part."),),
        ),
    )
