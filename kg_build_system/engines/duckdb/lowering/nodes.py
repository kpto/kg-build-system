"""The SQL AST node type used by the DuckDB lowerer.

sqlglot does not publish a public base-class alias that type checkers accept, so
the engine boundary names it once here. Lowering protocols remain generic over
the node type; only the DuckDB implementation uses this alias.
"""
from __future__ import annotations

from typing import Any

SqlNode = Any

__all__ = ["SqlNode"]
