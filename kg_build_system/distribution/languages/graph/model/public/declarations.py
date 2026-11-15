"""The concrete graph declaration an author writes."""
from __future__ import annotations

from typing import Any, ClassVar

from .options import GraphOptions


class Graph:
    """Base class for the project's one graph declaration.

    Declare the graph by subclassing ``Graph`` and assigning ``options``. The
    graph's name defaults to the class name in snake case. A namespace may
    contain at most one concrete graph declaration.

    Example:
        ```python
        from kg_build_system import (
            Claim, Graph, GraphOptions, Limitation, Purpose, Meaning,
        )

        class OpenTargetsGraph(Graph):
            options = GraphOptions(
                name="open_targets",
                description="Curated target-disease evidence.",
                meaning=Meaning(
                    purpose=Purpose(
                        text="Target prioritisation.",
                        limitations=(
                            Limitation("No literature mining."),
                        ),
                    ),
                    claims=(Claim("The graph describes associations."),),
                ),
            )
        ```
    """

    options: ClassVar[GraphOptions]
    _graph_options: ClassVar[GraphOptions]
    _graph_name: ClassVar[str]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        from ...service._private.declarations import prepare_graph_declaration

        prepare_graph_declaration(cls)


__all__ = ["Graph"]
