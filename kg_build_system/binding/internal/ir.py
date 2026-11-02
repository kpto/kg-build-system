"""Compilation IR for graph bindings."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from ...annotations.internal.ir import AnnotationIR
from ...expressions.internal.ir import ExpressionIR
from ...table.internal.ir import RowSourcePlanIR


@dataclass(frozen=True, slots=True)
class NodeBindingIR:
    """One node component bound from one row context."""

    symbol_id: str
    component: str
    build_key: ExpressionIR
    properties: tuple[tuple[str, ExpressionIR], ...]
    debug_name: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()
    kind: Literal["node"] = "node"
    row_source: RowSourcePlanIR | None = None


@dataclass(frozen=True, slots=True)
class EdgeBindingIR:
    """One edge component bound from one row context and two endpoint keys."""

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
    row_source: RowSourcePlanIR | None = None


BindingIR: TypeAlias = NodeBindingIR | EdgeBindingIR


__all__ = ["BindingIR", "EdgeBindingIR", "NodeBindingIR"]
