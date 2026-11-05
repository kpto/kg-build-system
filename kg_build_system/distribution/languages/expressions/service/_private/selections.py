"""Selection construction, struct navigation and authoring normalization."""
from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from kg_build_system.kernel.model.public.types import ArrayType, LogicalType, NullableType, StructType
from ...model.internal.model import Traversal
from ...model.public.selections.value import SelectedMember
from .apply import apply_operation
from .build import field_reference

if TYPE_CHECKING:
    from ...model.public.selections.value import ValueInput, ValueSelection
    from ...model.public.values import ValueExpression


def require_expression(selection: ValueSelection[Any]) -> ValueExpression[Any]:
    return selection.require_expression()


def _declaration(logical_type: StructType):
    from kg_build_system.kernel.model.public.types import Struct

    value: Any = importlib.import_module(logical_type.module)
    for part in logical_type.qualname.split("."):
        value = getattr(value, part)
    if not isinstance(value, type) or not issubclass(value, Struct):
        raise TypeError("struct logical type does not resolve to a Struct declaration")
    return value


def _extract_member(
    parent,
    selector,
    parent_type: StructType,
    *,
    propagate_null: bool,
):
    from ...model.internal.model import FieldReferenceExpression
    from ...model.public.selections.value import ValueSelection

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
    parent_model = parent.require_expression().model

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


def expand_selection(selection: ValueSelection[Any]):
    logical_type = selection.logical_type
    base = logical_type.value if isinstance(logical_type, NullableType) else logical_type
    if not isinstance(base, ArrayType):
        raise TypeError("expand requires an array selection")
    return select_expression_from_node(
        apply_operation("expand", require_expression(selection)).model
    )


def drop_null_selection(selection: ValueSelection[Any]):
    logical_type = selection.logical_type
    if not isinstance(logical_type, NullableType):
        raise TypeError("drop_null requires a nullable selection")
    return select_expression(
        apply_operation("drop_null", require_expression(selection))
    )


def drop_if_selection(
    selection: ValueSelection[Any],
    predicate: Callable[[Any], Any],
):
    from ...model.public.boolean import BoolExpression

    if not callable(predicate):
        raise TypeError("drop_if requires a callable predicate")
    result = predicate(selection)
    if not isinstance(result, BoolExpression):
        raise TypeError("drop_if predicates must return a BoolExpression")
    return select_expression(
        apply_operation("drop_if", require_expression(selection), result.model)
    )


def select_expression_from_node(expression):
    from ...model.public.selections.array import ArraySelection
    from ...model.public.selections.nullable import NullableSelection
    from ...model.public.selections.struct import StructSelection
    from ...model.public.selections.value import ValueSelection
    from ...model.public.values import ValueExpression
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
    from ...model.public.selections.array import ArraySelection
    from ...model.public.selections.nullable import NullableSelection
    from ...model.public.selections.struct import StructSelection
    from ...model.public.selections.value import ValueSelection

    member = SelectedMember(name, logical_type, declaration)
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
    from ...model.public.selections.value import ValueSelection
    from ...model.public.values import ValueExpression

    if isinstance(value, ValueSelection):
        return cast("ValueExpression[T]", require_expression(value))
    if isinstance(value, ValueExpression):
        return value
    raise TypeError("expected a value selection or value expression")


__all__ = [
    "SelectedMember", "as_expression", "drop_if_selection", "drop_null_selection",
    "expand_selection", "require_expression", "select_expression",
    "select_expression_from_node", "select_member",
]
