"""Implementation factories for the meta-graph module."""
from __future__ import annotations

from typing import Any


def compiler_for(configuration: Any, module_class: type[Any]) -> Any:
    """Create the meta-graph compiler for one configuration."""
    from ...._private.modules.meta_graph.compiler import MetaGraphCompiler

    return MetaGraphCompiler(configuration, module_class)


def executor_for(module_version: str) -> Any:
    """Create the meta-graph executor for one module version."""
    from ...._private.modules.meta_graph.executor import MetaGraphExecutor

    return MetaGraphExecutor(module_version)


__all__ = ["compiler_for", "executor_for"]
