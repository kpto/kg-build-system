"""The frozen authoring facts of one table declaration class."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kg_build_system.declaration.foundations.annotations.model.public import Annotation
from .fields import FieldSpec


@dataclass(frozen=True, slots=True)
class DeclarationSpec:
    """The facts a declaration class owns after class creation."""

    kind: str
    name: str | None
    description: str | None
    annotations: tuple[Annotation, ...]
    fields: tuple[FieldSpec, ...] = ()
    final: bool = True
    row_source: Any = None
    members: tuple[type[Any], ...] = ()


__all__ = ["DeclarationSpec"]
