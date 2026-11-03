"""The relational engine a build opens."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .duckdb import DuckDBRelationService, configure_framework_macros

if TYPE_CHECKING:
    from .duckdb.session import EngineSession, PINNED_TIME_ZONE, engine_session

__all__ = [
    "DuckDBRelationService",
    "EngineSession",
    "PINNED_TIME_ZONE",
    "configure_framework_macros",
    "engine_session",
]


def __getattr__(name: str) -> Any:
    if name in {"EngineSession", "PINNED_TIME_ZONE", "engine_session"}:
        from .duckdb import session

        return getattr(session, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
