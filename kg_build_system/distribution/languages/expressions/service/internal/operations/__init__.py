"""Built-in operation specifications and their composition."""
from __future__ import annotations

from ..._private.predicates import is_unit
from .registry import DEFAULT_OPERATIONS
from .spec import (
    ArgumentSpec, OperationRegistry, OperationSpec, ParameterSpec, RowEffectSpec,
)

__all__ = [
    "ArgumentSpec", "DEFAULT_OPERATIONS", "OperationRegistry", "OperationSpec",
    "ParameterSpec", "RowEffectSpec", "is_unit",
]
