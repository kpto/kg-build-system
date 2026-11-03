"""Emit the ``add`` expression operator."""
from __future__ import annotations

from sqlglot import exp

from .base import BinaryEmitter

ADD = BinaryEmitter(
    "add",
    lambda left, right: exp.Add(this=left, expression=right),
    "add requires two arguments",
)

__all__ = ["ADD"]
