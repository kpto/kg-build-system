"""The Neo4j import-bundle module's configuration."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..paths import validate_relative_path
from ..registration import ModuleRegistrationConfiguration


@dataclass(frozen=True)
class Neo4jModuleConfiguration(ModuleRegistrationConfiguration):
    """Where the Neo4j import bundle lands and how the script connects.

    ``relative_directory`` is the bundle directory beneath the build output
    directory, ``script_name`` a Python filename inside it, and
    ``default_database`` the database named by the generated script. The runtime
    field ``relative_directory`` may replace the directory for one build.

    Example:
        ```python
        from kg_build_system.distribution import (
            Neo4jModule, Neo4jModuleConfiguration, register_module,
        )

        modules = (
            register_module(
                Neo4jModule,
                Neo4jModuleConfiguration(relative_directory="neo4j-import"),
            ),
        )
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
        if not isinstance(self.default_database, str) or not self.default_database.strip():
            raise ValueError("Neo4j default database must be non-empty")


__all__ = ["Neo4jModuleConfiguration"]
