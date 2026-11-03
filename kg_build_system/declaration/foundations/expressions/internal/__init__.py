"""Framework-internal interface of the expression foundation.

The authoring families are in :mod:`...expressions.public`; this surface holds
the frozen model, operation specifications, row semantics, DTO codec and source
renderer.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .dto.blueprint_dto import (
    ExpressionDTO, ExpressionDTOBase, FieldReferenceDTO, LiteralExpressionDTO,
    OperationExpressionDTO, OperationParameterDTO, VariableExpressionDTO,
)
from .model import (
    PRESERVE_ROWS, Expression, ExpressionNode, FieldReferenceExpression,
    LiteralExpression, OperationExpression, OperationParameter, RowEffect,
    RowSemantics, Traversal, VariableExpression,
)

if TYPE_CHECKING:
    from .._private.coercion import expression_input
    from .._private.dto import expression_dto
    from .._private.literals import literal
    from .._private.semantics import (
        compose_row_semantics, row_effects, row_semantics,
    )
    from .dto import walk_expression_dto
    from .dto.codec import expression_from_document, expression_to_document
    from .service.build import field_reference, operation, with_arguments
    from .service.operations import (
        DEFAULT_OPERATIONS, ArgumentSpec, OperationRegistry, OperationSpec,
        ParameterSpec, RowEffectSpec, is_unit,
    )
    from .service.source import render_expression_source
    from .service.visitors import (
        ExpressionVisitor, rewrite_expression, visit_expression, walk_expression,
    )


LAZY_EXPORTS = {
    "DEFAULT_OPERATIONS": (".service.operations", "DEFAULT_OPERATIONS"),
    "ArgumentSpec": (".service.operations", "ArgumentSpec"),
    "ExpressionVisitor": (".service.visitors", "ExpressionVisitor"),
    "OperationRegistry": (".service.operations", "OperationRegistry"),
    "OperationSpec": (".service.operations", "OperationSpec"),
    "ParameterSpec": (".service.operations", "ParameterSpec"),
    "RowEffectSpec": (".service.operations", "RowEffectSpec"),
    "compose_row_semantics": (".._private.semantics", "compose_row_semantics"),
    "expression_dto": (".._private.dto", "expression_dto"),
    "expression_from_document": (".dto.codec", "expression_from_document"),
    "expression_input": (".._private.coercion", "expression_input"),
    "expression_to_document": (".dto.codec", "expression_to_document"),
    "field_reference": (".service.build", "field_reference"),
    "is_unit": (".service.operations", "is_unit"),
    "literal": (".._private.literals", "literal"),
    "operation": (".service.build", "operation"),
    "render_expression_source": (".service.source", "render_expression_source"),
    "rewrite_expression": (".service.visitors", "rewrite_expression"),
    "row_effects": (".._private.semantics", "row_effects"),
    "row_semantics": (".._private.semantics", "row_semantics"),
    "visit_expression": (".service.visitors", "visit_expression"),
    "walk_expression": (".service.visitors", "walk_expression"),
    "walk_expression_dto": (".dto", "walk_expression_dto"),
    "with_arguments": (".service.build", "with_arguments"),
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
    "DEFAULT_OPERATIONS", "PRESERVE_ROWS", "ArgumentSpec", "Expression",
    "ExpressionDTO", "ExpressionDTOBase", "ExpressionNode", "ExpressionVisitor",
    "FieldReferenceDTO", "FieldReferenceExpression", "LiteralExpression",
    "LiteralExpressionDTO", "OperationExpression", "OperationExpressionDTO",
    "OperationParameter", "OperationParameterDTO", "OperationRegistry",
    "OperationSpec", "ParameterSpec", "RowEffect", "RowEffectSpec",
    "RowSemantics", "Traversal", "VariableExpression", "VariableExpressionDTO",
    "compose_row_semantics", "expression_dto", "expression_from_document",
    "expression_input", "expression_to_document", "field_reference", "is_unit",
    "literal", "operation", "render_expression_source", "rewrite_expression",
    "row_effects", "row_semantics", "visit_expression", "walk_expression",
    "walk_expression_dto", "with_arguments",
]
