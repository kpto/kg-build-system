"""Implementation factories for the Neo4j module."""
from __future__ import annotations

from typing import Any


def compiler_for(configuration: Any, module_class: type[Any]) -> Any:
    """Create the Neo4j compiler for one configuration."""
    from ..._private.modules.neo4j.compiler import Neo4jCompiler

    return Neo4jCompiler(configuration, module_class)


def executor_for(context: Any) -> Any:
    """Create the Neo4j executor for one factory context."""
    from ..._private.modules.neo4j.executor import executor_for as create

    return create(context)


__all__ = ["compiler_for", "executor_for"]
