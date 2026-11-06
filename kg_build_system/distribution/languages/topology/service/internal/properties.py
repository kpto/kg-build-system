"""Property-descriptor construction interface for topology declarations."""
from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from kg_build_system.distribution.languages.annotations.model.public import (
    Annotation,
)

if TYPE_CHECKING:
    from kg_build_system.distribution.languages.semantics.model.public import (
        Semantics,
    )


def make_property(
    *, name: str | None = None, description: str | None = None,
    annotations: Sequence[Annotation] = (),
    semantics: Semantics | None = None,
) -> Any:
    """Build the descriptor assigned to a property slot."""
    from ...model._private.properties import make_property as build

    return build(
        name=name, description=description, annotations=annotations,
        semantics=semantics,
    )


__all__ = ["make_property"]
