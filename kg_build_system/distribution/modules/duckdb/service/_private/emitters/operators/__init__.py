"""DuckDB expression-emitter composition."""
from __future__ import annotations

from .registry import DEFAULT_OPERATORS, OPERATORS, compose_operators

__all__ = ["DEFAULT_OPERATORS", "OPERATORS", "compose_operators"]
