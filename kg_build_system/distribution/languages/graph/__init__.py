"""The graph language: the project's one graph declaration.

A graph declaration states the project's meaning root: its claims and the one
purpose under which its frames and limitations are read. A namespace may declare
zero graph declarations or exactly one.

Example:
    ```python
    from kg_build_system import (
        Claim, Frame, Graph, GraphOptions, GraphSemantics, Limitation, Purpose,
    )

    class OpenTargetsGraph(Graph):
        options = GraphOptions(
            name="open_targets",
            semantics=GraphSemantics(
                claims=(Claim("The graph describes associations."),),
                purpose=Purpose(
                    text="Target prioritisation.",
                    frames=(
                        Frame(
                            text="Curated evidence only.",
                            limitations=(Limitation("No literature mining."),),
                        ),
                    ),
                ),
            ),
        )
    ```
"""
from __future__ import annotations

from .model.public import Graph, GraphOptions

__all__ = ["Graph", "GraphOptions"]
