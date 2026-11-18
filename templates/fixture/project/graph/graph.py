"""The template's graph declaration.

This is the one project-level declaration. Its purpose says what the fixture is
for; replace it with the project's own graph and root meaning.
"""

from kg_build_system import Claim, Graph, GraphOptions, Limitation, Meaning, Purpose


class FixtureGraph(Graph):

    options = GraphOptions(
        name="fixture",
        meaning=Meaning(
            purpose=Purpose(
                "Exercise every authoring layer of the template so a new project "
                "starts with a passing build. Replace this graph with the project's "
                "graph.",
                limitations=(
                    Limitation(
                        "It models nothing in the user's domain; it is a conformance "
                        "fixture."
                    ),
                ),
            ),
            claims=(
                Claim("The fixture builds from the template's items source."),
            ),
        ),
    )
