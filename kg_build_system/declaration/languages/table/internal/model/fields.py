"""The frozen field facts the table language transcribes and renders."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kg_build_system.declaration.foundations.annotations.internal import Annotation
from kg_build_system.kernel.internal.types import LogicalType


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """A field resolved against one declaration class."""

    attribute: str
    name: str
    descriptor: Any
    logical_type: LogicalType
    access_type: LogicalType
    description: str | None = None
    annotations: tuple[Annotation, ...] = ()
    declaration: type[Any] | None = None


__all__ = ["FieldSpec"]
