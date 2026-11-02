"""Lower the ``and`` expression operator."""
from __future__ import annotations

from sqlglot import exp

from .base import BinaryLowerer

AND = BinaryLowerer(
    "and",
    lambda left, right: exp.And(this=left, expression=right),
    "and requires two arguments",
)

__all__ = ["AND"]
