"""Selection construction, struct navigation and authoring normalization."""
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any, cast

from ...types.internal import ArrayType, LogicalType, NullableType, StructType
from ..internal.build import field_reference
from ..internal.model import Traversal
from .apply import apply_operation

if TYPE_CHECKING:
    from ..public.selections.value import ValueInput, ValueSelection
    from ..public.values import ValueExpression


def _declaration(logical_type: StructType):
    from ...types.internal import Struct

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
    from ..internal.model import FieldReferenceExpression
    from ..public.selections.value import ValueSelection

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

    if isinstance(parent_model, FieldReferenceExpression):
        path = (*parent_model.path, member.name)
        traversals = list(parent_model.traversals)
        member_type = member.logical_type
        selected_base = (
            member_type.value
            if isinstance(member_type, NullableType)
            else member_type
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
    from ..public.selections.array import ArraySelection
    from ..public.selections.nullable import NullableSelection
    from ..public.selections.struct import StructSelection
    from ..public.selections.value import ValueSelection
    from ..public.values import ValueExpression
    from .factory import wrap_expression

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
    from ..public.selections.array import ArraySelection
    from ..public.selections.nullable import NullableSelection
    from ..public.selections.struct import StructSelection
    from ..public.selections.value import _SelectedMember, ValueSelection

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
    from ..public.selections.value import ValueSelection
    from ..public.values import ValueExpression

    if isinstance(value, ValueSelection):
        return cast("ValueExpression[T]", value._require_expression())
    if isinstance(value, ValueExpression):
        return value
    raise TypeError("expected a value selection or value expression")


__all__ = [
    "as_expression", "select_expression", "select_expression_from_node",
    "select_member",
]
