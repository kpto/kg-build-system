"""DuckDB row-source-emitter composition."""
from __future__ import annotations

from .registry import DEFAULT_ROW_SOURCES, FAMILIES, compose_row_sources

__all__ = ["DEFAULT_ROW_SOURCES", "FAMILIES", "compose_row_sources"]
