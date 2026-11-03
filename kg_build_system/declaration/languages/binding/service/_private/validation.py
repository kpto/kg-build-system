"""Invariant checks for the binding blueprint DTO."""
from __future__ import annotations

from typing import Any


def validate_binding(
    component: str,
    properties: tuple[tuple[str, Any], ...],
    mode: str,
    rows: Any,
) -> None:
    """Reject a binding whose target, properties or mode is incoherent."""
    if not component:
        raise ValueError("bindings require a non-empty component name")
    names = tuple(name for name, _ in properties)
    if any(not name for name in names):
        raise ValueError("binding property names must be non-empty")
    if len(names) != len(set(names)):
        raise ValueError("binding property names must be unique")
    if mode not in {"declarative", "python"}:
        raise ValueError(f"unknown binding mode {mode!r}")
    if mode == "python" and rows is None:
        raise ValueError("a python binding requires a row plan")
    if mode == "declarative" and rows is not None:
        raise ValueError("a declarative binding cannot carry a row plan")


__all__ = ["validate_binding"]
