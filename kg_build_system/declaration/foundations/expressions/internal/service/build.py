"""Factories for canonical field-reference and operation expressions."""
from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from typing import Any

from ......kernel.internal.json import freeze_json
from ......kernel.internal.types import LogicalType
from ..model import ExpressionNode, FieldReferenceExpression, OperationExpression, OperationParameter, RowSemantics, Traversal
from ..._private.semantics import compose_row_semantics


def field_reference(
    *,
    source: str,
    path: Sequence[str],
    logical_type: LogicalType,
    traversals: Sequence[Traversal] = (),
    row_semantics: RowSemantics = RowSemantics(),
) -> FieldReferenceExpression:
    """Build a field reference, the canonical form of a column or path read."""
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
    row_semantics: RowSemantics = RowSemantics(),
) -> OperationExpression:
    """Build a low-level operation expression.

    This constructor is the escape hatch for custom operations and for callers
    that already resolved the result type. Built-in authoring uses an
    :class:`OperationSpec` so arity, parameter and row-effect rules are stated
    once.
    """
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


def with_arguments(
    expression: OperationExpression, arguments: tuple[ExpressionNode, ...],
) -> OperationExpression:
    """An operation with a rewritten argument tuple."""
    if arguments == expression.arguments:
        return expression
    return dataclasses.replace(expression, arguments=arguments)


__all__ = ["field_reference", "operation", "with_arguments"]
