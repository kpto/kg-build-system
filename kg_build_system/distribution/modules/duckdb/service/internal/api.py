"""Thin re-export of the DuckDB executor, service and resource provider."""
from __future__ import annotations

from .._private.executor import DuckDbExecutor
from .._private.resources import DuckDbResourceProvider
from .._private.service import DuckDbService

__all__ = ["DuckDbExecutor", "DuckDbResourceProvider", "DuckDbService"]
