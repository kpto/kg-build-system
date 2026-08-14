"""DuckDB lowering for engine-neutral relational plans."""

from .lowering import lower_relation_sql

__all__ = ["lower_relation_sql"]
