"""Implementation factories for the exact-duplicate removal module."""
from __future__ import annotations

from typing import Any


def compiler_for(configuration: Any, module_class: type[Any]) -> Any:
    """Create the deduplication compiler for one configuration."""
    from ..._private.modules.deduplication.compiler import (
        DeduplicationCompiler,
    )

    return DeduplicationCompiler(configuration, module_class)


def executor_for() -> Any:
    """Create the deduplication executor."""
    from ..._private.modules.deduplication.executor import (
        DeduplicationExecutor,
    )

    return DeduplicationExecutor()


__all__ = ["compiler_for", "executor_for"]
