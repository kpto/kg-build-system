"""DTO for the graph language's blueprint part."""
from __future__ import annotations

from dataclasses import dataclass

from kg_build_system.distribution.languages.meaning.model.internal.dto import (
    MeaningDTO,
)


@dataclass(frozen=True, slots=True)
class GraphDeclarationDTO:
    """The project's one graph declaration in the blueprint.

    ``name`` is the portable graph name and ``meaning`` is the project's
    meaning root: the same ``MeaningDTO`` value every other declaration uses,
    carrying a required purpose. ``description`` is nullable prose.
    """

    name: str
    description: str | None
    meaning: MeaningDTO

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("a graph declaration name must be a non-empty string")
        if not isinstance(self.meaning, MeaningDTO):
            raise TypeError(
                "a graph declaration requires a Meaning with a purpose"
            )
        if self.meaning.purpose is None:
            raise ValueError(
                "a graph declaration requires a Meaning with a purpose"
            )
        if self.description is not None and (
            not isinstance(self.description, str) or not self.description
        ):
            raise ValueError(
                "a graph declaration description must be null or a non-empty string"
            )


__all__ = ["GraphDeclarationDTO"]
