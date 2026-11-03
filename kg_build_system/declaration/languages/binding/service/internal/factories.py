"""Binding-factory interface for the author-facing builders."""
from __future__ import annotations

from typing import Any


def node_binding(**values: Any) -> Any:
    """Validate one node binding and return its frozen value."""
    from .._private.factories import node_binding as build

    return build(**values)


def edge_binding(**values: Any) -> Any:
    """Validate one edge binding and return its frozen value."""
    from .._private.factories import edge_binding as build

    return build(**values)


__all__ = ["edge_binding", "node_binding"]
