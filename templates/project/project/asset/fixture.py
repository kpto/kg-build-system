"""The fixture asset: the template's neutral source unit.

This is a conformance fixture, not a domain model. It exists so a new project
starts with a source that exercises the asset and relation layers. Replace it
with the project's own asset.
"""

from pathlib import Path

from kg_build_system import (
    Asset,
    AssetAuthority,
    AssetLayout,
    AssetOptions,
    AssetProfile,
    Claim,
    Limitation,
    Meaning,
    Purpose,
)

DATA = Path(__file__).parent.parent / "data"


class Fixture(Asset):

    options = AssetOptions(
        name="fixture",
        version="template",
        profile=AssetProfile(
            subject="template fixture records",
            coverage="items and their parts",
            authority=AssetAuthority.PRIMARY,
            basis="the template's conformance fixture",
        ),
        layout=AssetLayout(
            kind="json",
            locator=str(DATA),
            format="json",
            members={"items": "items.json"},
        ),
        meaning=Meaning(
            purpose=Purpose(
                "Exercise the template's asset layer and give the fixture a source. "
                "Replace it with the project's asset.",
                limitations=(
                    Limitation(
                        "It is a conformance fixture, not an asset of the user's domain."
                    ),
                ),
            ),
            claims=(
                Claim("The fixture source holds items with nested parts."),
            ),
        ),
    )
