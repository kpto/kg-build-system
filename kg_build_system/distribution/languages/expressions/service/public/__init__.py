"""Author-facing selection constructors and operation handles."""
from __future__ import annotations

from .boolean import all_of, any_of
from .expression import value_expression
from .operations import (
    DEFAULT_OPERATIONS, ArgumentSpec, Operation, OperationRegistry,
    OperationSpec, ParameterSpec, RowEffectSpec, apply_operation,
)

__all__ = [
    "DEFAULT_OPERATIONS", "ArgumentSpec", "Operation", "OperationRegistry",
    "OperationSpec", "ParameterSpec", "RowEffectSpec", "all_of",
    "any_of", "apply_operation", "value_expression",
]
