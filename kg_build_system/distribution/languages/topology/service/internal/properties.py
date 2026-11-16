"""Property-descriptor construction interface for topology declarations."""
from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from kg_build_system.distribution.languages.annotations.model.public import (
    Annotation,
)

if TYPE_CHECKING:
    from kg_build_system.distribution.languages.meaning.model.public import (
        Meaning,
        Omitted,
    )


def make_property(
    *, name: str | None = None,
    annotations: Sequence[Annotation] = (),
    meaning: Meaning | type[Omitted],
) -> Any:
    """Build the descriptor assigned to a property slot."""
    from ...model._private.properties import make_property as build

    return build(
        name=name, annotations=annotations, meaning=meaning,
    )


__all__ = ["make_property"]
