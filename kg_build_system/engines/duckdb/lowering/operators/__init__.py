"""Composition of DuckDB expression lowerers.

Each family exports a tuple. Composition happens once, at import, and rejects a
duplicate operator name so two implementations cannot silently shadow one
another.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping

from ....protocols import ExpressionLowerer
from . import array, boolean, numeric, other, row_effect, struct, text

FAMILIES = (
    numeric.OPERATORS,
    boolean.OPERATORS,
    text.OPERATORS,
    array.OPERATORS,
    struct.OPERATORS,
    row_effect.OPERATORS,
    other.OPERATORS,
)


def compose_operators(
    *groups: Iterable[ExpressionLowerer],
) -> Mapping[str, ExpressionLowerer]:
    registry: dict[str, ExpressionLowerer] = {}
    for group in groups:
        for lowerer in group:
            if not lowerer.operator:
                raise ValueError("expression lowerers require a non-empty operator")
            if lowerer.operator in registry:
                raise ValueError(
                    f"duplicate expression operator {lowerer.operator!r}"
                )
            registry[lowerer.operator] = lowerer
    return registry


DEFAULT_OPERATORS = compose_operators(*FAMILIES)

__all__ = ["DEFAULT_OPERATORS", "FAMILIES", "compose_operators"]
