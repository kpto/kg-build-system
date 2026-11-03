"""The Neo4j administrative-import target module."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from ....kernel import ExecutorFactoryContext
from ...internal.adapters.kernel_module import KernelModule
from ...public.model.registration import ModuleRegistrationConfiguration


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
        from ..._private.modules.neo4j.configuration import validate

        validate(
            relative_directory=self.relative_directory,
            script_name=self.script_name,
            default_database=self.default_database,
        )


class Neo4jModule(KernelModule):
    """Export one Parquet file per component and a Neo4j import script.

    The module refuses property types its import format cannot represent and
    edges whose endpoints are not bound concrete nodes. The bundle is published
    as ``neo4j/import_bundle`` and configured by ``Neo4jModuleConfiguration``.

    Example:
        ```python
        from kg_build_system.distribution import (
            Neo4jModule, Neo4jModuleConfiguration, register_module,
        )

        modules = (
            register_module(
                Neo4jModule, Neo4jModuleConfiguration(),
            ),
        )
        ```
    """

    ID: ClassVar[str] = "neo4j"
    VERSION: ClassVar[str] = "2"
    CONFIGURATION_TYPE: ClassVar[type[Neo4jModuleConfiguration]] = (
        Neo4jModuleConfiguration
    )

    @classmethod
    def compiler(cls, configuration: Any) -> Any:
        """Create the compiler for this module version."""
        from ..._private.modules.neo4j.compiler import Neo4jCompiler

        return Neo4jCompiler(configuration)

    @classmethod
    def executor(cls, context: ExecutorFactoryContext) -> Any:
        """Create the executor for this module version."""
        from ..._private.modules.neo4j.executor import executor_for

        return executor_for(context)


__all__ = ["Neo4jModule", "Neo4jModuleConfiguration"]
