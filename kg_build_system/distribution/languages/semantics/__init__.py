"""The semantics language: claims, purpose, frames and limitations.

A semantics value states what a graph or one declaration means. ``GraphSemantics``
is the project's meaning root; ``Semantics`` is a declaration fragment read under
that root. Claims are contextless, limitations belong to a frame, and a frame
scopes the limitation space within a purpose.

Example:
    ```python
    from kg_build_system.distribution.languages.semantics import (
        Claim, Frame, GraphSemantics, Limitation, Purpose, Semantics,
    )

    graph_semantics = GraphSemantics(
        claims=(Claim("The graph describes gene-disease associations."),),
        purpose=Purpose(
            text="Target prioritisation.",
            frames=(
                Frame(
                    text="Curated evidence only.",
                    limitations=(Limitation("No literature mining."),),
                ),
            ),
        ),
    )
    ```
"""
from __future__ import annotations

from .model.public import (
    Claim,
    Frame,
    GraphSemantics,
    Limitation,
    Purpose,
    Semantics,
)

__all__ = ["Claim", "Frame", "GraphSemantics", "Limitation", "Purpose", "Semantics"]
