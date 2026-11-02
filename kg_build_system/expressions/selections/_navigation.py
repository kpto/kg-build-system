"""Selection construction, struct navigation and authoring normalization.

The selection classes live in their family modules. This module owns the rules
that choose a family and turn one selection or expression into another, using
late imports so the family modules stay independent of each other.
"""
from __future__ import annotations

import importlib
from typing import Any, cast

from ...types.interfaces import ArrayType, LogicalType, NullableType, StructType
from .._apply import apply_operation
from .._build import field_reference
from .._model import Traversal
from ..values import ValueExpression
from .value import ValueInput, ValueSelection, _SelectedMember


def _declaration(logical_type: StructType):
    from ...types.interfaces import Struct

    value: Any = importlib.import_module(logical_type.module)
    for part in logical_type.qualname.split("."):
        value = getattr(value, part)
    if not isinstance(value, type) or not issubclass(value, Struct):
        raise TypeError("struct logical type does not resolve to a Struct declaration")
    return value


def _pick(
    parent,
    selector,
    parent_type: StructType,
    *,
    propagate_null: bool,
):
    proxy = object.__new__(_declaration(parent_type))
    selected = selector(proxy)
    if not isinstance(selected, ValueSelection) or selected._member is None:
        raise TypeError("struct selectors must return a declared field selection")
    member = selected._member
    if member.declaration != parent_type:
        raise TypeError(
            "struct selectors must return a field from their input declaration"
        )
    result_type = member.logical_type
    if propagate_null and not isinstance(result_type, NullableType):
        result_type = NullableType(result_type)
    parent_model = parent._require_expression().model
    from .._model import FieldReferenceExpression

    if isinstance(parent_model, FieldReferenceExpression):
        path = (*parent_model.path, member.name)
        traversals = list(parent_model.traversals)
        selected_base = (
            member.logical_type.value
            if isinstance(member.logical_type, NullableType)
            else member.logical_type
        )
        if isinstance(selected_base, StructType):
            traversals.append(Traversal("struct", path))
        elif isinstance(selected_base, ArrayType):
            traversals.append(Traversal("array", path))
        result = field_reference(
            source=parent_model.source,
            path=path,
            logical_type=result_type,
            traversals=traversals,
            row_semantics=parent_model.row_semantics,
        )
    else:
        result = apply_operation(
            "struct_field",
            parent_model,
            result_type=result_type,
            name=member.name,
        ).model
    return select_expression_from_node(result)


def _expand(expression: ValueExpression[Any]):
    return select_expression_from_node(apply_operation("expand", expression.model))


def select_expression_from_node(expression):
    from ..factory import wrap_expression
    from .array import ArraySelection
    from .nullable import NullableSelection
    from .struct import StructSelection
    from .value import ValueSelection

    if not isinstance(expression, ValueExpression):
        expression = wrap_expression(expression)
    logical_type = expression.logical_type
    if isinstance(logical_type, NullableType):
        return NullableSelection(expression)
    if isinstance(logical_type, ArrayType):
        return ArraySelection(expression)
    if isinstance(logical_type, StructType):
        return StructSelection(expression)
    return ValueSelection(expression)


def select_expression[T](expression: ValueExpression[T]) -> ValueSelection[T]:
    """Wrap a bindable expression in the selection matching its logical shape."""
    return cast("ValueSelection[T]", select_expression_from_node(expression))


def select_member(
    name: str, logical_type: LogicalType, declaration: StructType,
) -> ValueSelection[Any]:
    """Create the temporary selection returned by a field on a struct proxy."""
    from .array import ArraySelection
    from .nullable import NullableSelection
    from .struct import StructSelection

    member = _SelectedMember(name, logical_type, declaration)
    base = logical_type.value if isinstance(logical_type, NullableType) else logical_type
    if isinstance(logical_type, NullableType):
        return NullableSelection(member=member)
    if isinstance(base, ArrayType):
        return ArraySelection(member=member)
    if isinstance(base, StructType):
        return StructSelection(member=member)
    return ValueSelection(member=member)


def as_expression[T](value: ValueInput[T]) -> ValueExpression[T]:
    """Normalize a terminal authoring input to its bindable expression."""
    if isinstance(value, ValueSelection):
        return cast("ValueExpression[T]", value._require_expression())
    if isinstance(value, ValueExpression):
        return value
    raise TypeError("expected a value selection or value expression")


__all__ = [
    "as_expression", "select_expression", "select_expression_from_node",
    "select_member",
]
