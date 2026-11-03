"""Framework SQL macros this engine expects on a build connection.

The macro name and statement are engine data; this module re-exports the one
definition for the private engine implementation.
"""
from __future__ import annotations

from .....model.internal.engine import NULL_GUARD_MACRO, NULL_GUARD_MACRO_SQL

__all__ = ["NULL_GUARD_MACRO", "NULL_GUARD_MACRO_SQL"]
