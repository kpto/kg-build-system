"""Compilation-only transfer objects for graph bindings."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from ..annotations.dto import AnnotationDTO
from ..expressions.dto import ExpressionDTO


@dataclass(frozen=True, slots=True)
class NodeBindingDTO:
    symbol_id: str
    component: str
    build_key: ExpressionDTO
    properties: tuple[tuple[str, ExpressionDTO], ...]
    debug_name: str | None = None
    annotations: tuple[AnnotationDTO, ...] = ()
    kind: Literal["node"] = "node"


@dataclass(frozen=True, slots=True)
class EdgeBindingDTO:
    symbol_id: str
    component: str
    build_key: ExpressionDTO
    source_build_key: ExpressionDTO
    target_build_key: ExpressionDTO
    properties: tuple[tuple[str, ExpressionDTO], ...]
    debug_name: str | None = None
    annotations: tuple[AnnotationDTO, ...] = ()
    kind: Literal["edge"] = "edge"


BindingDTO: TypeAlias = NodeBindingDTO | EdgeBindingDTO

__all__ = ["BindingDTO", "EdgeBindingDTO", "NodeBindingDTO"]
