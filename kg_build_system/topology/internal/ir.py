"""Compilation-only IR for graph topology.

The declaration classes are authoring syntax. Everything a compiler or a target
module reads is a frozen value in this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ...annotations.internal.ir import AnnotationIR
from ...types.internal.ir import LogicalTypeIR


@dataclass(frozen=True, slots=True)
class PropertyIR:
    """One declared graph property lowered to its logical type."""

    name: str
    logical_type: LogicalTypeIR
    description: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()


@dataclass(frozen=True, slots=True)
class ComponentIR:
    """One graph-visible node or edge component."""

    symbol_id: str
    name: str
    kind: Literal["node", "edge"]
    properties: tuple[PropertyIR, ...] = ()
    description: str | None = None
    source: str | None = None
    target: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()
    abstract: bool = False
    parent: str | None = None


__all__ = ["ComponentIR", "PropertyIR"]
