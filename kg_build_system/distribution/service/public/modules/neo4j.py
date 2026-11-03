"""The Neo4j administrative-import module class."""
from __future__ import annotations

from typing import Any, ClassVar

from .....kernel import ExecutorFactoryContext
from ....model.public.modules.neo4j import Neo4jModuleConfiguration
from ...internal.adapters.kernel_module import KernelModule


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
        from ...internal.modules.neo4j import compiler_for

        return compiler_for(configuration, cls)

    @classmethod
    def executor(cls, context: ExecutorFactoryContext) -> Any:
        """Create the executor for this module version."""
        from ...internal.modules.neo4j import executor_for

        return executor_for(context)


__all__ = ["Neo4jModule"]
