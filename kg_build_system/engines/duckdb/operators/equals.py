"""Lower the ``equals`` expression operator."""
from __future__ import annotations

from sqlglot import exp

from .base import BinaryLowerer

EQUALS = BinaryLowerer(
    "equals",
    lambda left, right: exp.EQ(this=left, expression=right),
    "equals requires two arguments",
)

__all__ = ["EQUALS"]
