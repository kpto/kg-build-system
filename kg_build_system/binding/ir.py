"""Compilation-only IR for graph bindings."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from ..annotations.ir import AnnotationIR
from ..expressions.ir import ExpressionIR


@dataclass(frozen=True, slots=True)
class NodeBindingIR:
    symbol_id: str
    component: str
    build_key: ExpressionIR
    properties: tuple[tuple[str, ExpressionIR], ...]
    debug_name: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()
    kind: Literal["node"] = "node"


@dataclass(frozen=True, slots=True)
class EdgeBindingIR:
    symbol_id: str
    component: str
    build_key: ExpressionIR
    source_build_key: ExpressionIR
    target_build_key: ExpressionIR
    properties: tuple[tuple[str, ExpressionIR], ...]
    debug_name: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()
    source_node: str | None = None
    target_node: str | None = None
    kind: Literal["edge"] = "edge"


BindingIR: TypeAlias = NodeBindingIR | EdgeBindingIR

__all__ = ["BindingIR", "EdgeBindingIR", "NodeBindingIR"]
