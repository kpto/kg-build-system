"""Configuration of the Neo4j import bundle."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kg_build_system.distribution.model.public.paths import validate_relative_path


@dataclass(frozen=True, slots=True)
class Neo4jConfiguration:
    """Where the Neo4j import bundle lands and how the script connects.

    ``relative_directory`` is the bundle directory beneath the build output
    directory, ``script_name`` a Python filename inside it, and
    ``default_database`` the database named by the generated script.

    Example:
        ```python
        from kg_build_system.distribution.executors.neo4j import Neo4jConfiguration

        configuration = Neo4jConfiguration(relative_directory="neo4j/current")
        assert configuration.script_name == "import_neo4j.py"
        ```
    """

    relative_directory: str = "neo4j-import"
    script_name: str = "import_neo4j.py"
    default_database: str = "neo4j"

    def __post_init__(self) -> None:
        validate_relative_path(
            self.relative_directory, context="Neo4j output directory",
        )
        validate_relative_path(self.script_name, context="Neo4j script name")
        if (
            len(Path(self.script_name).parts) != 1
            or not self.script_name.endswith(".py")
        ):
            raise ValueError("Neo4j script name must be a Python filename")
        if (
            not isinstance(self.default_database, str)
            or not self.default_database.strip()
        ):
            raise ValueError("Neo4j default database must be non-empty")


__all__ = ["Neo4jConfiguration"]
