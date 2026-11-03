"""Implementation factories for the core module."""
from __future__ import annotations

from typing import Any


def compiler_for(module_class: type[Any]) -> Any:
    """Create the core compiler for one module class."""
    from ..._private.modules.core.compiler import CoreCompiler

    return CoreCompiler(module_class)


def executor_for() -> Any:
    """Create the core executor."""
    from ..._private.modules.core.executor import CoreExecutor

    return CoreExecutor()


__all__ = ["compiler_for", "executor_for"]
