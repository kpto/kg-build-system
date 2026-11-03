"""Stable internal path for the relational engine a build opens.

The implementation lives in the build package's private zone; this module only
delegates so the engine remains importable by its interface path.
"""
from __future__ import annotations

from ..._private.engine import (
    DuckDBRelationService,
    configure_framework_macros,
)
from ..._private.engine.duckdb.session import (
    EngineSession,
    PINNED_TIME_ZONE,
    engine_session,
)

__all__ = [
    "DuckDBRelationService",
    "EngineSession",
    "PINNED_TIME_ZONE",
    "configure_framework_macros",
    "engine_session",
]
