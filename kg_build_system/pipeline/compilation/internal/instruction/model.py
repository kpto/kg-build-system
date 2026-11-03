"""Instruction-emitter plans and shared emission values."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PythonReference:
    """A stable reference to a Python callable, not a live callable itself."""

    module: str
    qualname: str
    signature: str


@dataclass(frozen=True, slots=True)
class SqlEmissionContext:
    """The facts an SQL emitter may add beside the rendered statement."""

    relation: str | None = None


__all__ = ["PythonReference", "SqlEmissionContext"]
