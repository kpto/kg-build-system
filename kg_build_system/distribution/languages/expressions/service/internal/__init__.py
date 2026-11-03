"""Expression service-internal interface: operations, codec, traversal and render."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .construction import wrap_expression
from .selections import as_expression, select_expression, select_member

if TYPE_CHECKING:
    from .._private.coercion import expression_input
    from .._private.dto import expression_dto, walk_expression_dto
    from .._private.literals import literal
    from .._private.semantics import (
        compose_row_semantics, row_effects, row_semantics,
    )
    from .build import field_reference, operation, with_arguments
    from .construction import literal as public_literal
    from .dto.codec import expression_from_document, expression_to_document
    from .operations import (
        DEFAULT_OPERATIONS, ArgumentSpec, OperationRegistry, OperationSpec,
        ParameterSpec, RowEffectSpec, is_unit,
    )
    from .source import render_expression_source
    from .visitors import (
        ExpressionVisitor, rewrite_expression, visit_expression, walk_expression,
    )


LAZY_EXPORTS = {
    "DEFAULT_OPERATIONS": (".operations", "DEFAULT_OPERATIONS"),
    "ArgumentSpec": (".operations", "ArgumentSpec"),
    "ExpressionVisitor": (".visitors", "ExpressionVisitor"),
    "OperationRegistry": (".operations", "OperationRegistry"),
    "OperationSpec": (".operations", "OperationSpec"),
    "ParameterSpec": (".operations", "ParameterSpec"),
    "RowEffectSpec": (".operations", "RowEffectSpec"),
    "compose_row_semantics": (".._private.semantics", "compose_row_semantics"),
    "expression_dto": (".._private.dto", "expression_dto"),
    "expression_from_document": (".dto.codec", "expression_from_document"),
    "expression_input": (".._private.coercion", "expression_input"),
    "expression_to_document": (".dto.codec", "expression_to_document"),
    "field_reference": (".build", "field_reference"),
    "is_unit": (".operations", "is_unit"),
    "literal": (".._private.literals", "literal"),
    "operation": (".build", "operation"),
    "render_expression_source": (".source", "render_expression_source"),
    "rewrite_expression": (".visitors", "rewrite_expression"),
    "row_effects": (".._private.semantics", "row_effects"),
    "row_semantics": (".._private.semantics", "row_semantics"),
    "visit_expression": (".visitors", "visit_expression"),
    "walk_expression": (".visitors", "walk_expression"),
    "walk_expression_dto": (".._private.dto", "walk_expression_dto"),
    "with_arguments": (".build", "with_arguments"),
}


def __getattr__(name: str):
    target = LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = target
    from importlib import import_module

    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value


__all__ = [
    "DEFAULT_OPERATIONS", "ArgumentSpec", "ExpressionVisitor", "OperationRegistry",
    "OperationSpec", "ParameterSpec", "RowEffectSpec", "as_expression",
    "compose_row_semantics", "expression_dto", "expression_from_document",
    "expression_input", "expression_to_document", "field_reference", "is_unit",
    "literal", "operation", "render_expression_source", "rewrite_expression",
    "row_effects", "row_semantics", "select_expression", "select_member",
    "visit_expression", "walk_expression", "walk_expression_dto",
    "with_arguments", "wrap_expression",
]
