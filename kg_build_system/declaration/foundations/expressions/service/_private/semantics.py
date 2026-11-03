"""Rules that derive one row-semantics value from another.

The row-semantics model is frozen data; composition and decomposition are
functions beside it so the data stays portable.
"""
from __future__ import annotations

from ...model.internal.model import ExpressionNode, RowEffect, RowSemantics


def row_effects(semantics: RowSemantics) -> tuple[RowEffect, ...]:
    """The ordered row effects one expression requires."""
    if semantics.mode == "preserve":
        return ()
    return (*semantics.upstream, RowEffect(semantics.mode, semantics.scope))


def row_semantics(effects: tuple[RowEffect, ...]) -> RowSemantics:
    """The semantics a full effect sequence denotes."""
    if not effects:
        return RowSemantics()
    return RowSemantics(effects[-1].mode, effects[-1].scope, effects[:-1])


def compose_row_semantics(
    *expressions: ExpressionNode, local: RowSemantics = RowSemantics(),
) -> RowSemantics:
    """Compose input and local row effects, sharing identical expansions."""
    effects: list[RowEffect] = []
    for expression in expressions:
        for effect in row_effects(expression.row_semantics):
            if effect.mode == "expand" and effect in effects:
                continue
            effects.append(effect)
    for effect in row_effects(local):
        if effect.mode == "expand" and effect in effects:
            continue
        effects.append(effect)
    return row_semantics(tuple(effects))


__all__ = ["compose_row_semantics", "row_effects", "row_semantics"]
