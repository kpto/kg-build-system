"""Apply one registered operation to authoring arguments."""
from __future__ import annotations

from typing import Any

from .operations import DEFAULT_OPERATIONS


def apply_operation(operator: str, *arguments: Any, **parameters: Any):
    """Build the typed expression for a registered operation."""
    return DEFAULT_OPERATIONS[operator].apply(*arguments, **parameters)


__all__ = ["apply_operation"]
