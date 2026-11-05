"""Factories for canonical field-reference and operation expressions."""
from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from typing import Any

from kg_build_system.distribution.model.public.refs import RelationRef
from kg_build_system.kernel.model.internal.json import freeze_json
from kg_build_system.kernel.model.public.types import LogicalType
from ...model.internal.model import (
    ExpressionNode, FieldReferenceExpression, LookupExpression,
    OperationExpression, OperationParameter, RowSemantics, Traversal,
)
from .semantics import compose_row_semantics


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
    **named_parameters: Any,
) -> OperationExpression:
    """Build a low-level operation expression.

    Named parameters may be passed either as a mapping or as keyword arguments;
    the source renderer uses the keyword form so its output is valid Python.
    """
    merged = dict(parameters or {})
    merged.update(named_parameters)
    frozen_parameters = tuple(
        OperationParameter(name, freeze_json(value))
        for name, value in sorted(merged.items())
    )
    return OperationExpression(
        operator=operator,
        arguments=tuple(arguments),
        parameters=frozen_parameters,
        logical_type=logical_type,
        row_semantics=compose_row_semantics(*arguments, local=row_semantics),
    )


def lookup_expression(
    relation: RelationRef,
    key: ExpressionNode,
    *,
    target_field: str,
    logical_type: LogicalType,
) -> LookupExpression:
    """Build a typed lookup expression from a target relation and a key."""
    return LookupExpression(
        relation=relation,
        target_field=target_field,
        key=key,
        logical_type=logical_type,
        row_semantics=compose_row_semantics(key),
    )


def with_arguments(
    expression: OperationExpression, arguments: tuple[ExpressionNode, ...],
) -> OperationExpression:
    """An operation with a rewritten argument tuple."""
    if arguments == expression.arguments:
        return expression
    return dataclasses.replace(expression, arguments=arguments)


__all__ = [
    "field_reference", "lookup_expression", "operation", "with_arguments",
]
