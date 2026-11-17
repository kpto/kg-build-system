"""The fixture item record."""

from kg_build_system import (
    Claim,
    Limitation,
    Meaning,
    Node,
    NodeOptions,
    PropertySlot,
    Purpose,
    property,
)


class ItemNode(Node):

    options = NodeOptions(
        name="item",
        meaning=Meaning(
            purpose=Purpose(
                "Exercise a source-backed record with one scalar property in the "
                "template fixture.",
                limitations=(
                    Limitation(
                        "A conformance fixture; replace it with the project's record."
                    ),
                ),
            ),
            claims=(Claim("One item has one label in the fixture source."),),
        ),
    )

    label: PropertySlot[str] = property(
        meaning=Meaning(
            claims=(Claim("The item's label as the fixture source writes it."),),
        ),
    )

    greeting: PropertySlot[str] = property(
        meaning=Meaning(
            claims=(
                Claim("The item label rendered by the project's hello operation."),
            ),
        ),
    )
