"""Factories for canonical field-reference and operation expressions."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from kg_build_system.distribution.model.public.refs import RelationRef
from kg_build_system.kernel.model.public.types import LogicalType
from ...model.internal.model import (
    ExpressionNode, FieldReferenceExpression, LookupExpression,
    OperationExpression, RowSemantics, Traversal,
)


def field_reference(
    *,
    source: str,
    path: Sequence[str],
    logical_type: LogicalType,
    traversals: Sequence[Traversal] = (),
    row_semantics: RowSemantics = RowSemantics(),
) -> FieldReferenceExpression:
    """Build a field reference, the canonical form of a column or path read."""
    from .._private.build import field_reference as build

    return build(
        source=source,
        path=path,
        logical_type=logical_type,
        traversals=traversals,
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

    This constructor is the escape hatch for custom operations and for callers
    that already resolved the result type. Built-in authoring uses an
    :class:`OperationSpec` so arity, parameter and row-effect rules are stated
    once.
    """
    from .._private.build import operation as build

    return build(
        operator,
        *arguments,
        logical_type=logical_type,
        parameters=parameters,
        row_semantics=row_semantics,
        **named_parameters,
    )


def lookup_expression(
    relation: RelationRef,
    key: ExpressionNode,
    *,
    target_field: str,
    logical_type: LogicalType,
) -> LookupExpression:
    """Build a typed lookup expression from a target relation and a key."""
    from .._private.build import lookup_expression as build

    return build(
        relation,
        key,
        target_field=target_field,
        logical_type=logical_type,
    )


def with_arguments(
    expression: OperationExpression, arguments: tuple[ExpressionNode, ...],
) -> OperationExpression:
    """An operation with a rewritten argument tuple."""
    from .._private.build import with_arguments as replace_arguments

    return replace_arguments(expression, arguments)


__all__ = [
    "field_reference", "lookup_expression", "operation", "with_arguments",
]
