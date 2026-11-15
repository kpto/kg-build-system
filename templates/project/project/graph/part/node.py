"""The fixture part record."""

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


class PartNode(Node):
    """One part in the template fixture."""

    options = NodeOptions(
        name="part",
        meaning=Meaning(
            purpose=Purpose(
                "Exercise a record reached through a private unnest stage in the "
                "template fixture.",
                limitations=(
                    Limitation(
                        "A conformance fixture; replace it with the project's record."
                    ),
                ),
            ),
            claims=(
                Claim("One part belongs to one item and carries one value."),
            ),
        ),
    )

    value: PropertySlot[float | None] = property(
        meaning=Meaning(
            claims=(Claim("The part's value as the fixture source writes it."),),
        ),
    )
