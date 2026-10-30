"""Numeric expression operators."""
from __future__ import annotations

from sqlglot import exp

from .base import BinaryLowerer

ADD = BinaryLowerer(
    "add",
    lambda left, right: exp.Add(this=left, expression=right),
    "add requires two arguments",
)
SUBTRACT = BinaryLowerer(
    "subtract",
    lambda left, right: exp.Sub(this=left, expression=right),
    "subtract requires two arguments",
)

OPERATORS = (ADD, SUBTRACT)

__all__ = ["OPERATORS"]
