"""Implementation factories for the file module."""
from __future__ import annotations

from typing import Any


def compiler_for(configuration: Any, module_class: type[Any]) -> Any:
    """Create the file compiler for one configuration and module class."""
    from ..._private.modules.file.compiler import FileCompiler

    return FileCompiler(configuration, module_class)


def executor_for(context: Any) -> Any:
    """Create the file executor for one factory context."""
    from ..._private.modules.file.executor import executor_for as create

    return create(context)


__all__ = ["compiler_for", "executor_for"]
