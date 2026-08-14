"""Compilation-only IR for graph topology."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..annotations.ir import AnnotationIR
from ..types.ir import LogicalTypeIR


@dataclass(frozen=True, slots=True)
class PropertyIR:
    name: str
    logical_type: LogicalTypeIR
    description: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()


@dataclass(frozen=True, slots=True)
class ComponentIR:
    symbol_id: str
    name: str
    kind: Literal["node", "edge"]
    properties: tuple[PropertyIR, ...] = ()
    description: str | None = None
    source: str | None = None
    target: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()


__all__ = ["ComponentIR", "PropertyIR"]
