"""Implementation factories for the compatible-facts merging module."""
from __future__ import annotations

from typing import Any


def compiler_for(configuration: Any, module_class: type[Any]) -> Any:
    """Create the merging compiler for one configuration and module class."""
    from ..._private.modules.merging.compiler import MergingCompiler

    return MergingCompiler(configuration, module_class)


def executor_for() -> Any:
    """Create the merging executor."""
    from ..._private.modules.merging.executor import MergingExecutor

    return MergingExecutor()


__all__ = ["compiler_for", "executor_for"]
