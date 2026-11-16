"""The one graph declaration for the monitored estate.

The declaration carries the project's root meaning: one expected use, the
limitations of that use and the claims that hold across the release.
"""

from kg_build_system import Claim, Graph, GraphOptions, Limitation, Meaning, Purpose


class EstateGraph(Graph):
    """The monitored estate and the records the build publishes for it."""

    options = GraphOptions(
        name="estate",
        meaning=Meaning(
            purpose=Purpose(
                "Estate condition review: for one site or unit, read the equipment "
                "installed there, the defects the surveys reported against it, and the "
                "observations and readings behind each defect.",
                limitations=(
                    Limitation(
                        "Covers the published 2026-08 register and survey export only; "
                        "an unregistered site, unit or visit is absent."
                    ),
                    Limitation(
                        "It is not a maintenance history, a work-order system or a "
                        "compliance record."
                    ),
                ),
            ),
            claims=(
                Claim("The export is the authority for the entities it names."),
                Claim(
                    "Every recorded relation states the stage that asserted it and the "
                    "date it is asserted as at."
                ),
            ),
        ),
    )
