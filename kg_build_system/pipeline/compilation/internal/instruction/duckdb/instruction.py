"""DuckDB SQL instruction emitter wrapper.

The SQL emission mechanism lives in ``_private.instructions``; this wrapper keeps
the internal instruction path stable.
"""
from __future__ import annotations

from ...._private.instructions.duckdb.instruction import (
    DuckDbSqlEmitter as _DuckDbSqlEmitter,
)


class DuckDbSqlEmitter(_DuckDbSqlEmitter):
    """Emit a DuckDB SQL instruction from an engine-neutral relation plan."""


__all__ = ["DuckDbSqlEmitter"]
