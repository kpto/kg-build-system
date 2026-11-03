"""Validation of the Neo4j module configuration."""
from __future__ import annotations

from pathlib import Path

from ...service.paths import validate_relative_path


def validate(
    *,
    relative_directory: str,
    script_name: str,
    default_database: str,
) -> None:
    """Reject an output path outside the build and an unusable script name."""
    validate_relative_path(
        relative_directory, context="Neo4j output directory",
    )
    validate_relative_path(script_name, context="Neo4j script name")
    if len(Path(script_name).parts) != 1 or not script_name.endswith(".py"):
        raise ValueError("Neo4j script name must be a Python filename")
    if not isinstance(default_database, str) or not default_database.strip():
        raise ValueError("Neo4j default database must be non-empty")


__all__ = ["validate"]
