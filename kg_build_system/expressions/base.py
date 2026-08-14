"""Factories for canonical field-reference and operation expressions."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..types import LogicalType
from .models import (
    ExpressionNode, FieldReferenceExpression, FrozenJson, FrozenObject, OperationExpression,
    OperationParameter, PRESERVE_ROWS, RowEffect, RowSemantics, Traversal,
)


def compose_row_semantics(
    *expressions: ExpressionNode, local: RowSemantics = PRESERVE_ROWS,
) -> RowSemantics:
    """Compose input and local row effects, sharing identical expansions."""
    effects: list[RowEffect] = []
    for expression in expressions:
        for effect in expression.row_semantics.effects:
            if effect.mode == "expand" and effect in effects:
                continue
            effects.append(effect)
    for effect in local.effects:
        if effect.mode == "expand" and effect in effects:
            continue
        effects.append(effect)
    return RowSemantics.from_effects(tuple(effects))


def freeze_json(value: Any) -> FrozenJson:
    """Convert JSON-compatible input into an immutable canonical value."""
    if value is None or type(value) in {str, int, float, bool}:
        return value
    if isinstance(value, Mapping):
        items = tuple(sorted(((str(key), freeze_json(item)) for key, item in value.items()), key=lambda item: item[0]))
        if len(items) != len({key for key, _ in items}):
            raise ValueError("JSON object keys must be unique after string normalization")
        return FrozenObject(items)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(freeze_json(item) for item in value)
    raise TypeError(f"expression metadata must be JSON-compatible, not {value!r}")


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


__all__ = ["compose_row_semantics", "field_reference", "freeze_json", "operation"]
