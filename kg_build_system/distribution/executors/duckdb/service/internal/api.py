"""Thin re-export of the DuckDB executor and its resource provider."""
from __future__ import annotations

from .._private.executor import DuckDbExecutor
from .._private.resources import DuckDbResourceProvider

__all__ = ["DuckDbExecutor", "DuckDbResourceProvider"]
