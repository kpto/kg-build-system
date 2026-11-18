"""The project's one graph declaration.

Replace the placeholder purpose with the decision the graph supports, for whom,
and what it is explicitly not for. Every record and relation in the project is
read under this purpose.
"""

from kg_build_system import Graph, GraphOptions, Meaning, Purpose


class ProjectGraph(Graph):

    options = GraphOptions(
        name="project",
        meaning=Meaning(
            purpose=Purpose(
                "Replace this with the decision the graph supports, for whom, "
                "and what it is not for."
            ),
        ),
    )
