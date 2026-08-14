"""Portable expression declarations and constructors."""
from .collection import collection
from .core import Expression, ExpressionValue, PermittedExpressionValue, ValueRef, item_type
from .inputs import ExpressionInput, to_expression
from .lookup import lookup
from .value import value
from .base import field_reference, operation
from .codec import decode_expression, encode_expression
from .ir import (
    ExpressionIR, ExpressionNode, FieldReferenceExpression, LiteralExpression,
    OperationExpression, OperationParameter, PRESERVE_ROWS, RowSemantics, Traversal,
)
from .literals import literal
from .visitors import ExpressionVisitor, rewrite_expression, visit_expression, walk_expression

__all__ = [
    "Expression", "ExpressionIR", "ExpressionInput", "ExpressionNode", "ExpressionValue",
    "ExpressionVisitor", "FieldReferenceExpression", "LiteralExpression", "OperationExpression",
    "OperationParameter", "PRESERVE_ROWS", "PermittedExpressionValue", "RowSemantics",
    "Traversal", "ValueRef", "collection", "decode_expression", "encode_expression",
    "field_reference", "item_type", "literal", "lookup", "operation", "rewrite_expression",
    "to_expression", "value", "visit_expression", "walk_expression",
]
