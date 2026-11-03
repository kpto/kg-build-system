"""Implementation factories for the conflict-validation module."""
from __future__ import annotations

from typing import Any


def compiler_for(configuration: Any, module_class: type[Any]) -> Any:
    """Create the conflict-validation compiler for one configuration."""
    from ..._private.modules.conflict_validation.compiler import (
        ConflictValidationCompiler,
    )

    return ConflictValidationCompiler(configuration, module_class)


def executor_for() -> Any:
    """Create the conflict-validation executor."""
    from ..._private.modules.conflict_validation.executor import (
        ConflictValidationExecutor,
    )

    return ConflictValidationExecutor()


__all__ = ["compiler_for", "executor_for"]
