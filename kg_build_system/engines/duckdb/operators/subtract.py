"""Lower the ``subtract`` expression operator."""
from __future__ import annotations

from sqlglot import exp

from .base import BinaryLowerer

SUBTRACT = BinaryLowerer(
    "subtract",
    lambda left, right: exp.Sub(this=left, expression=right),
    "subtract requires two arguments",
)

__all__ = ["SUBTRACT"]
