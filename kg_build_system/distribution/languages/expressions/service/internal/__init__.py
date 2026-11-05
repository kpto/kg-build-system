"""Expression service-internal interface: operations, codec, traversal and render."""
from __future__ import annotations

from .adapters.kernel_language import ExpressionsLanguage
from .build import field_reference, operation, with_arguments
from .construction import wrap_expression
from .dto.codec import expression_from_document, expression_to_document
from .functions import (
    authoring_references, compose_row_semantics, expression_dto,
    expression_field_path, expression_input, expression_references,
    field_reference_for, literal, row_effects, row_semantics,
    walk_expression_dto,
)
from .operations import (
    DEFAULT_OPERATIONS, ArgumentSpec, OperationRegistry, OperationSpec,
    ParameterSpec, RowEffectSpec, is_unit,
)
from .selections import as_expression, select_expression, select_member
from .source import render_expression_source
from .visitors import (
    ExpressionVisitor, rewrite_expression, visit_expression, walk_expression,
)

__all__ = [
    "DEFAULT_OPERATIONS", "ArgumentSpec", "ExpressionVisitor",
    "ExpressionsLanguage", "OperationRegistry", "OperationSpec",
    "ParameterSpec", "RowEffectSpec", "as_expression", "authoring_references",
    "compose_row_semantics",
    "expression_dto", "expression_field_path", "expression_from_document",
    "expression_input", "expression_references", "expression_to_document",
    "field_reference", "field_reference_for", "is_unit", "literal",
    "operation", "render_expression_source", "rewrite_expression",
    "row_effects", "row_semantics", "select_expression", "select_member",
    "visit_expression", "walk_expression", "walk_expression_dto",
    "with_arguments", "wrap_expression",
]
