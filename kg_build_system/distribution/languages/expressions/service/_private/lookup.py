"""Authoring-time resolution of a lookup target and its key column."""
from __future__ import annotations

from typing import Any

from kg_build_system.distribution.model.public.refs import RelationRef
from kg_build_system.kernel import Key
from kg_build_system.kernel.model.public.types import (
    ArrayType, LogicalType, NullableType, StructType,
)

from ...model.internal.model import (
    FieldReferenceExpression, LookupExpression, OperationExpression,
)


def _declaration_name(value: Any) -> str:
    spec = vars(value).get("_kg_declaration_spec") if isinstance(value, type) else None
    if spec is not None:
        name = getattr(spec, "name", None)
        if isinstance(name, str) and name:
            return name
    for attribute in ("_table_name", "_projection_name"):
        name = getattr(value, attribute, None)
        if isinstance(name, str) and name:
            return name
    name = getattr(value, "__name__", None)
    if isinstance(name, str) and name:
        return name
    raise TypeError(
        "a lookup target must be a named table, projection or relation reference"
    )


def _target(target: Any) -> tuple[RelationRef, LogicalType]:
    if isinstance(target, RelationRef):
        return target, StructType("data", target.name)
    source = (
        target.row_source()
        if isinstance(target, type) and callable(getattr(target, "row_source", None))
        else target
    )
    declaration = getattr(source, "source", target)
    shape = getattr(source, "shape", target)
    relation = RelationRef("data", Key((_declaration_name(declaration),)))
    if not isinstance(shape, type):
        raise TypeError("a lookup target must expose a row shape")
    return relation, StructType(shape.__module__, shape.__qualname__)


def _field_name(expression: Any) -> str | None:
    if isinstance(expression, FieldReferenceExpression):
        return expression.path[-1] if expression.path else None
    if isinstance(expression, OperationExpression):
        names = {
            name for argument in expression.arguments
            if (name := _field_name(argument)) is not None
        }
        if len(names) == 1:
            return names.pop()
    return None


def _target_field(key: Any, target_key: Any) -> str:
    if isinstance(target_key, str):
        if not target_key:
            raise ValueError("lookup target key columns must be non-empty")
        return target_key
    if target_key is not None:
        from .selections import as_expression

        name = _field_name(as_expression(target_key).model)
        if name is not None:
            return name
        raise TypeError(
            "lookup target_key must name a declared field or a target column string"
        )
    from .selections import as_expression

    name = _field_name(as_expression(key).model)
    if name is None:
        raise TypeError(
            "lookup requires an explicit target_key when the key is not a field read"
        )
    return name


def lookup_value(
    relation: Any,
    key: Any,
    *,
    target_key: Any = None,
):
    """Build the value selection of an array of matching target records.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.service.internal import (
            lookup_value,
        )

        value = lookup_value(Target, Source.key)
        ```
    """
    from .selections import as_expression, selection_from_node

    key_node = as_expression(key).model
    relation_ref, target_type = _target(relation)
    result = LookupExpression(
        relation=relation_ref,
        target_field=_target_field(key_node, target_key),
        key=key_node,
        logical_type=NullableType(ArrayType(target_type)),
    )
    return selection_from_node(result)


__all__ = ["lookup_value"]
