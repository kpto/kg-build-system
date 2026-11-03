"""Emit the ``equals`` expression operator."""
from __future__ import annotations

from sqlglot import exp

from .base import BinaryEmitter

EQUALS = BinaryEmitter(
    "equals",
    lambda left, right: exp.EQ(this=left, expression=right),
    "equals requires two arguments",
)

__all__ = ["EQUALS"]
