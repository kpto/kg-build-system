"""The frozen field facts the data language transcribes and renders."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from kg_build_system.distribution.languages.annotations.model.public import Annotation
from kg_build_system.kernel.model.public.types import LogicalType

if TYPE_CHECKING:
    from kg_build_system.distribution.languages.meaning.model.public import (
        Meaning,
    )
    from ...public.fields import FieldDefinition


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """A field resolved against one declaration class."""

    attribute: str
    name: str
    descriptor: Any
    logical_type: LogicalType
    access_type: LogicalType
    annotations: tuple[Annotation, ...] = ()
    declaration: type[Any] | None = None
    meaning: Meaning | None = None
    definition: FieldDefinition | None = None


__all__ = ["FieldSpec"]
