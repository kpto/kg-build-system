"""Options an author assigns to the one graph declaration.

The options carry the graph's portable name, an optional description and the
project's meaning root. The meaning root is a ``GraphSemantics`` with exactly one
purpose; a graph declaration cannot exist without one.
"""
from __future__ import annotations

from dataclasses import dataclass

from kg_build_system.distribution.languages.semantics.model.public import (
    GraphSemantics,
    Purpose,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class GraphOptions:
    """Everything an author states about the project's graph.

    ``semantics`` is required and must be a ``GraphSemantics`` carrying a
    ``Purpose``. ``name`` defaults to the declaration class name in snake case.

    Example:
        ```python
        from kg_build_system import (
            Claim, Frame, GraphOptions, GraphSemantics, Limitation, Purpose,
        )

        options = GraphOptions(
            name="open_targets",
            description="Curated target-disease evidence.",
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

    name: str | None = None
    description: str | None = None
    semantics: GraphSemantics

    def __post_init__(self) -> None:
        if not isinstance(self.semantics, GraphSemantics):
            raise TypeError("graph options semantics must be GraphSemantics")
        if not isinstance(self.semantics.purpose, Purpose):
            raise TypeError("graph options semantics must carry a Purpose")
        if self.name is not None and (
            not isinstance(self.name, str) or not self.name
        ):
            raise ValueError("a graph name must be null or a non-empty string")
        if self.description is not None and (
            not isinstance(self.description, str) or not self.description
        ):
            raise ValueError(
                "a graph description must be null or a non-empty string"
            )


__all__ = ["GraphOptions"]
