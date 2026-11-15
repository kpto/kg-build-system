"""The graph language: the project's one graph declaration.

A graph declaration states the project's meaning root: one ``Meaning`` value
carrying the root purpose and its claims. A namespace may declare zero graph
declarations or exactly one.

Example:
    ```python
    from kg_build_system import (
        Claim, Graph, GraphOptions, Limitation, Purpose, Meaning,
    )

    class OpenTargetsGraph(Graph):
        options = GraphOptions(
            name="open_targets",
            meaning=Meaning(
                purpose=Purpose(
                    text="Target prioritisation.",
                    limitations=(Limitation("No literature mining."),),
                ),
                claims=(Claim("The graph describes associations."),),
            ),
        )
    ```
"""
from __future__ import annotations

from .model.public import Graph, GraphOptions

__all__ = ["Graph", "GraphOptions"]
