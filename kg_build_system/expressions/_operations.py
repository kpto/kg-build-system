"""Functions over the expression domain model.

The models in :mod:`.models` are frozen data; the rules that derive one value
from another live here so that the data stays portable and inspectable.
"""
from __future__ import annotations

from dataclasses import replace

from .models import ExpressionNode, OperationExpression, RowEffect, RowSemantics


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


def with_arguments(
    expression: OperationExpression, arguments: tuple[ExpressionNode, ...],
) -> OperationExpression:
    """An operation with a rewritten argument tuple."""
    return expression if arguments == expression.arguments else replace(
        expression, arguments=arguments,
    )


__all__ = ["row_effects", "row_semantics", "with_arguments"]
