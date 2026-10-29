"""Factories for canonical field-reference and operation expressions."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .._frozen_json import freeze_json
from ..types.interfaces import LogicalType
from ._operations import row_effects, row_semantics
from .models import (
    ExpressionNode, FieldReferenceExpression, OperationExpression,
    OperationParameter, PRESERVE_ROWS, RowEffect, RowSemantics, Traversal,
)


def compose_row_semantics(
    *expressions: ExpressionNode, local: RowSemantics = PRESERVE_ROWS,
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


def field_reference(
    *, source: str, path: Sequence[str], logical_type: LogicalType,
    traversals: Sequence[Traversal] = (), row_semantics: RowSemantics = PRESERVE_ROWS,
) -> FieldReferenceExpression:
    return FieldReferenceExpression(
        source=source,
        path=tuple(path),
        traversals=tuple(traversals),
        logical_type=logical_type,
        row_semantics=row_semantics,
    )


def operation(
    operator: str,
    *arguments: ExpressionNode,
    logical_type: LogicalType,
    parameters: Mapping[str, Any] | None = None,
    row_semantics: RowSemantics = PRESERVE_ROWS,
) -> OperationExpression:
    frozen_parameters = tuple(
        OperationParameter(name, freeze_json(value))
        for name, value in sorted((parameters or {}).items())
    )
    return OperationExpression(
        operator=operator,
        arguments=tuple(arguments),
        parameters=frozen_parameters,
        logical_type=logical_type,
        row_semantics=compose_row_semantics(*arguments, local=row_semantics),
    )


__all__ = ["compose_row_semantics", "field_reference", "operation"]
