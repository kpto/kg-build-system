"""Lower the ``or`` expression operator."""
from __future__ import annotations

from sqlglot import exp

from .base import BinaryLowerer

OR = BinaryLowerer(
    "or",
    lambda left, right: exp.Or(this=left, expression=right),
    "or requires two arguments",
)

__all__ = ["OR"]
