"""Compilation-only transfer objects for graph topology."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..annotations.dto import AnnotationDTO
from ..types.dto import LogicalTypeDTO


@dataclass(frozen=True, slots=True)
class PropertyDTO:
    name: str
    logical_type: LogicalTypeDTO
    description: str | None = None
    annotations: tuple[AnnotationDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class ComponentDTO:
    symbol_id: str
    name: str
    kind: Literal["node", "edge"]
    properties: tuple[PropertyDTO, ...] = ()
    description: str | None = None
    source: str | None = None
    target: str | None = None
    annotations: tuple[AnnotationDTO, ...] = ()


__all__ = ["ComponentDTO", "PropertyDTO"]
