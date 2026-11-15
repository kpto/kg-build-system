"""Options an author assigns to the one graph declaration.

The options carry the graph's portable name, an optional description and the
project's meaning root. The root is a ``Semantics`` value carrying exactly one
purpose; a graph declaration cannot exist without one.
"""
from __future__ import annotations

from dataclasses import dataclass

from kg_build_system.distribution.languages.semantics.model.public import (
    Purpose,
    Semantics,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class GraphOptions:
    """Everything an author states about the project's graph.

    ``semantics`` is required and must be a ``Semantics`` value carrying a
    ``Purpose``. ``name`` defaults to the declaration class name in snake case.

    Example:
        ```python
        from kg_build_system import (
            Claim, GraphOptions, Limitation, Purpose, Semantics,
        )

        options = GraphOptions(
            name="open_targets",
            description="Curated target-disease evidence.",
            semantics=Semantics(
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
    semantics: Semantics

    def __post_init__(self) -> None:
        if not isinstance(self.semantics, Semantics):
            raise TypeError("graph options semantics must be a Semantics value")
        if not isinstance(self.semantics.purpose, Purpose):
            raise TypeError(
                "a graph declaration requires a Semantics with a purpose"
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
