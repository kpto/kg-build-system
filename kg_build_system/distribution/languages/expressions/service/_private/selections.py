"""Selection construction, navigation, array/value algebra and authoring helpers."""
from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from kg_build_system.kernel.model.public.types import (
    BOOL,
    INT,
    STR,
    ArrayType,
    LogicalType,
    NullableType,
    StructType,
)
from ...model.internal.model import (
    ExpressionNode,
    FieldReferenceExpression,
    SelectedMember,
    Traversal,
)
from .apply import apply_operation
from .build import field_reference

if TYPE_CHECKING:
    from ...model.public.selection import Selection
    from ...model.public.values import ValueExpression


def _selection_class():
    from ...model.public.selection import Selection

    return Selection


def require_expression(selection: "Selection[Any]") -> "ValueExpression[Any]":
    """Return the private expression behind a selection."""
    from ...model.public.values import ValueExpression

    node = getattr(selection, "_node", None)
    if not isinstance(node, ExpressionNode):
        raise TypeError("a struct member selection is only valid inside extract")
    return cast("ValueExpression[Any]", _wrap_expression(node))


def _wrap_expression(node: ExpressionNode) -> "ValueExpression[Any]":
    from .factory import wrap_expression

    return wrap_expression(node)


def selection_from_node(node: ExpressionNode) -> "Selection[Any]":
    """Wrap one compiler expression node in the single authoring type."""
    return _selection_class()(node)


def select_expression(expression: Any) -> "Selection[Any]":
    """Wrap a bindable expression or node in the single authoring type."""
    from ...model.public.values import ValueExpression

    if isinstance(expression, ValueExpression):
        return selection_from_node(expression.model)
    if isinstance(expression, ExpressionNode):
        return selection_from_node(expression)
    raise TypeError("select_expression requires an expression or expression node")


def select_member(
    name: str, logical_type: LogicalType, declaration: StructType,
) -> "Selection[Any]":
    """Create the temporary selection returned by a field on a struct proxy."""
    return _selection_class()(
        member=SelectedMember(name, logical_type, declaration),
    )


def as_expression(value: Any) -> "ValueExpression[Any]":
    """Normalize a terminal authoring input to its private expression."""
    from ...model.public.selection import Selection
    from ...model.public.values import ValueExpression

    if isinstance(value, Selection):
        return require_expression(value)
    if isinstance(value, ValueExpression):
        return value
    if isinstance(value, ExpressionNode):
        return _wrap_expression(value)
    raise TypeError("expected a selection or value expression")


def _declaration(logical_type: StructType) -> type[Any]:
    from kg_build_system.kernel.model.public.types import Shape

    if logical_type.module == "kg_build_system.distribution.languages.expressions.model.public.pair":
        from .pair import pair_declaration

        generated = pair_declaration(logical_type.qualname)
        if generated is not None:
            return generated
    value: Any = importlib.import_module(logical_type.module)
    for part in logical_type.qualname.split("."):
        value = getattr(value, part)
    if not isinstance(value, type) or not issubclass(value, Shape):
        raise TypeError(
            "struct logical type does not resolve to a Shape declaration"
        )
    return value


def _base(logical_type: LogicalType) -> LogicalType:
    return logical_type.value if isinstance(logical_type, NullableType) else logical_type


def extract_member(
    parent: "Selection[Any]", selector: Callable[[Any], "Selection[Any]"],
) -> "Selection[Any]":
    """Build a member selection from a declared struct and compose presence."""
    from ...model.public.selection import Selection

    parent_type = _base(parent.logical_type)
    if not isinstance(parent_type, StructType):
        raise TypeError("extract requires a struct selection")
    proxy = object.__new__(_declaration(parent_type))
    selected = selector(proxy)
    if not isinstance(selected, Selection):
        raise TypeError("struct selectors must return a declared field selection")
    member = selected._member
    if member is not None:
        if member.declaration != parent_type:
            raise TypeError(
                "struct selectors must return a field from their input declaration"
            )
        member_name = member.name
        member_type = member.logical_type
    else:
        node = selected._node
        if not isinstance(node, FieldReferenceExpression) or not node.path:
            raise TypeError(
                "struct selectors must return a declared field selection"
            )
        member_name = node.path[-1]
        member_type = node.logical_type
    result_type = member_type
    if isinstance(parent.logical_type, NullableType) and not isinstance(
        result_type, NullableType
    ):
        result_type = NullableType(result_type)
    parent_model = parent._node
    if parent_model is None:
        raise TypeError("extract requires a value expression")
    if isinstance(parent_model, FieldReferenceExpression):
        path = (*parent_model.path, member_name)
        traversals = list(parent_model.traversals)
        selected_base = _base(member_type)
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
            name=member_name,
        ).model
    return selection_from_node(result)


def _array_base(selection: "Selection[Any]") -> ArrayType:
    base = _base(selection.logical_type)
    if not isinstance(base, ArrayType):
        raise TypeError("an array selection is required")
    return base


def array_operation(selection: "Selection[Any]", operator: str) -> "Selection[Any]":
    """Apply a null-preserving array operator."""
    _array_base(selection)
    return selection_from_node(
        apply_operation(operator, require_expression(selection).model).model
    )


def array_at(
    selection: "Selection[Any]", index: int | Selection[int],
) -> "Selection[Any]":
    """Index an array; the result is nullable for out-of-bounds."""
    _array_base(selection)
    from .coercion import expression_input

    node = require_expression(selection).model
    return selection_from_node(
        apply_operation("array_at", node, expression_input(index, INT)).model
    )


def array_slice(
    selection: "Selection[Any]",
    start: int | Selection[int],
    end: int | Selection[int],
) -> "Selection[Any]":
    """Keep an array range."""
    _array_base(selection)
    from .coercion import expression_input

    node = require_expression(selection).model
    return selection_from_node(
        apply_operation(
            "array_slice",
            node,
            expression_input(start, INT),
            expression_input(end, INT),
        ).model
    )


def zip_arrays(
    left: "Selection[Any]", right: "Selection[Any]",
) -> "Selection[Any]":
    """Pair two array selections by position."""
    _array_base(left)
    _array_base(right)
    return selection_from_node(
        apply_operation(
            "zip",
            require_expression(left).model,
            require_expression(right).model,
        ).model
    )


def array_concat(selection: "Selection[Any]", separator: str) -> "Selection[Any]":
    """Join an array of non-null strings with ``separator``."""
    _array_base(selection)
    from .coercion import expression_input

    node = require_expression(selection).model
    return selection_from_node(
        apply_operation("join", node, expression_input(separator, STR)).model
    )


def transform_items(
    selection: "Selection[Any]",
    selector: Callable[["Selection[Any]"], "Selection[Any]"],
) -> "Selection[Any]":
    """Apply a selector to every array item."""
    from .arrays import _transform_items

    return selection_from_node(
        _transform_items(require_expression(selection), selector).model
    )


def null_items_removed(selection: "Selection[Any]") -> "Selection[Any]":
    """Drop null items from an array."""
    from .arrays import _drop_null_items

    return selection_from_node(
        _drop_null_items(require_expression(selection)).model
    )


def text_concat(
    selection: "Selection[Any]", value: Any, *, prepend: bool,
) -> "Selection[Any]":
    from .coercion import expression_input

    node = require_expression(selection).model
    other = expression_input(value, STR)
    arguments = (other, node) if prepend else (node, other)
    return selection_from_node(
        apply_operation("concat", *arguments, result_type=STR).model
    )


def text_replace(
    selection: "Selection[Any]", search: str, replacement: str,
) -> "Selection[Any]":
    from .coercion import expression_input

    node = require_expression(selection).model
    return selection_from_node(
        apply_operation(
            "replace",
            node,
            expression_input(search, STR),
            expression_input(replacement, STR),
        ).model
    )


def text_equals(selection: "Selection[Any]", value: Any) -> "Selection[Any]":
    from .coercion import expression_input

    node = require_expression(selection).model
    return selection_from_node(
        apply_operation("equals", node, expression_input(value, STR)).model
    )


def separator_text(
    selection: "Selection[Any]",
    separator: str,
    occurrence: int,
    side: str,
    include_separator: bool,
) -> "Selection[Any]":
    from .coercion import expression_input

    node = require_expression(selection).model
    operator = "before_separator" if side == "before" else "after_separator"
    return selection_from_node(
        apply_operation(
            operator,
            node,
            expression_input(separator, STR),
            occurrence=occurrence,
            include_separator=include_separator,
        ).model
    )


def numeric_binary(
    selection: "Selection[Any]", operator: str, other: Any,
) -> "Selection[Any]":
    from .coercion import expression_input

    logical_type = selection.logical_type
    node = require_expression(selection).model
    operand = expression_input(other, logical_type)
    return selection_from_node(
        apply_operation(operator, node, operand).model
    )


def boolean_unary(selection: "Selection[Any]", operator: str) -> "Selection[Any]":
    node = require_expression(selection).model
    return selection_from_node(apply_operation(operator, node).model)


def boolean_binary(
    selection: "Selection[Any]", operator: str, other: Any,
) -> "Selection[Any]":
    from .coercion import expression_input

    node = require_expression(selection).model
    return selection_from_node(
        apply_operation(operator, node, expression_input(other, BOOL)).model
    )


def scalar_to_string(selection: "Selection[Any]") -> "Selection[Any]":
    node = require_expression(selection).model
    return selection_from_node(apply_operation("to_string", node).model)


def default_to(selection: "Selection[Any]", value: Any) -> "Selection[Any]":
    from .coercion import expression_input

    logical_type = selection.logical_type
    if not isinstance(logical_type, NullableType):
        raise TypeError("default_to requires a nullable selection")
    node = require_expression(selection).model
    fallback = expression_input(value, logical_type.value)
    return selection_from_node(
        apply_operation("coalesce", node, fallback).model
    )


# --------------------------------------------------------------------------
# Row-effect operations used by the one-shot handles.


def drop_null_rows(selection: "Selection[Any]") -> "Selection[Any]":
    if not isinstance(selection.logical_type, NullableType):
        raise TypeError("drop_null requires a nullable selection")
    return selection_from_node(
        apply_operation("drop_null", require_expression(selection).model).model
    )


def drop_if_rows(
    selection: "Selection[Any]", predicate: Callable[[Any], Any],
) -> "Selection[Any]":
    from ...model.public.selection import Selection

    if not callable(predicate):
        raise TypeError("drop_if requires a callable predicate")
    result = predicate(selection)
    if not isinstance(result, Selection) or _base(result.logical_type) != BOOL:
        raise TypeError("drop_if predicates must return a Selection[bool]")
    return selection_from_node(
        apply_operation(
            "drop_if",
            require_expression(selection).model,
            require_expression(result).model,
        ).model
    )


def expand_rows(selection: "Selection[Any]") -> "Selection[Any]":
    if not isinstance(_base(selection.logical_type), ArrayType):
        raise TypeError("expand requires an array selection")
    return selection_from_node(
        apply_operation("expand", require_expression(selection).model).model
    )


__all__ = [
    "SelectedMember", "array_at", "array_concat", "array_operation",
    "array_slice", "as_expression", "boolean_binary", "boolean_unary",
    "default_to", "drop_if_rows", "drop_null_rows", "expand_rows",
    "extract_member", "null_items_removed", "numeric_binary",
    "require_expression", "scalar_to_string", "select_expression",
    "select_member", "selection_from_node", "separator_text", "text_concat",
    "text_equals", "text_replace", "transform_items", "zip_arrays",
]
