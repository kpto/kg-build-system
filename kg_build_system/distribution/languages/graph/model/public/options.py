"""Options an author assigns to the one graph declaration.

The options carry the graph's portable name, an optional description and the
project's meaning root. The root is a ``Meaning`` value carrying exactly one
purpose; a graph declaration cannot exist without one.
"""
from __future__ import annotations

from dataclasses import dataclass

from kg_build_system.distribution.languages.meaning.model.public import (
    Purpose,
    Meaning,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class GraphOptions:
    """Everything an author states about the project's graph.

    ``meaning`` is required and must be a ``Meaning`` value carrying a
    ``Purpose``. ``name`` defaults to the declaration class name in snake case.

    Example:
        ```python
        from kg_build_system import (
            Claim, GraphOptions, Limitation, Purpose, Meaning,
        )

        options = GraphOptions(
            name="open_targets",
            description="Curated target-disease evidence.",
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

    name: str | None = None
    description: str | None = None
    meaning: Meaning

    def __post_init__(self) -> None:
        if not isinstance(self.meaning, Meaning):
            raise TypeError("graph options meaning must be a Meaning value")
        if not isinstance(self.meaning.purpose, Purpose):
            raise TypeError(
                "a graph declaration requires a Meaning with a purpose"
            )
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
