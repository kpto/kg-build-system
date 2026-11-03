"""Framework-internal interface of the expression foundation.

The authoring families are in :mod:`...expressions.public`; this surface holds
the frozen model, operation specifications, row semantics, DTO codec and source
renderer.
"""
from __future__ import annotations

from .._private.coercion import expression_input
from .._private.dto import expression_dto
from .._private.literals import literal
from .._private.semantics import compose_row_semantics, row_effects, row_semantics
from .dto.blueprint_dto import (
    ExpressionDTO, ExpressionDTOBase, FieldReferenceDTO, LiteralExpressionDTO,
    OperationExpressionDTO, OperationParameterDTO, VariableExpressionDTO,
    walk_expression_dto,
)
from .dto.codec import expression_from_document, expression_to_document
from .model import (
    PRESERVE_ROWS, Expression, ExpressionNode, FieldReferenceExpression,
    LiteralExpression, OperationExpression, OperationParameter, RowEffect,
    RowSemantics, Traversal, VariableExpression,
)
from .service import (
    DEFAULT_OPERATIONS, ArgumentSpec, ExpressionVisitor, OperationRegistry,
    OperationSpec, ParameterSpec, RowEffectSpec, field_reference, is_unit,
    operation, render_expression_source, rewrite_expression, visit_expression,
    walk_expression, with_arguments,
)

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
