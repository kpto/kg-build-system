"""Property-descriptor construction interface for topology declarations."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from kg_build_system.declaration.foundations.annotations.model.public import (
    Annotation,
)


def make_property(
    *, name: str | None = None, description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Any:
    """Build the descriptor assigned to a property slot."""
    from ...model._private.properties import make_property as build

    return build(name=name, description=description, annotations=annotations)


__all__ = ["make_property"]
