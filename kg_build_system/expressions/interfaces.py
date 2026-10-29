"""Framework-internal interface of the expression domain.

Other subpackages import the canonical expression model, its operations and its
codecs here. The author-facing selections are re-exported by
:mod:`kg_build_system.expressions`; the compilation IR is
:mod:`kg_build_system.expressions.ir`.
"""
from __future__ import annotations

from ._operations import row_effects, row_semantics, with_arguments
from .arrays import ArrayExpression
from .base import field_reference, operation
from .boolean import BoolExpression, all_of, any_of
from .codec import decode_expression, encode_expression
from .custom import CustomDataTypeExpression
from .factory import value_expression, wrap_expression
from .ir_codec import decode_expression_ir, encode_expression_ir, walk_expression_ir
from .literals import literal
from .mapping import expression_to_ir
from .models import (
    PRESERVE_ROWS,
    Expression,
    ExpressionNode,
    FieldReferenceExpression,
    LiteralExpression,
    OperationExpression,
    OperationParameter,
    RowEffect,
    RowSemantics,
    Traversal,
    VariableExpression,
)
from .nullable import NullableExpression
from .numeric import FloatExpression, IntExpression, NumberExpression
from .selections import (
    ArraySelection,
    NullableDataType,
    NullableSelection,
    SelectionDataType,
    SelectionStructured,
    SelectionUnit,
    StructSelection,
    ValueInput,
    ValueSelection,
    as_expression,
    select_expression,
    select_member,
)
from .structs import StructExpression
from .text import StrExpression
from .values import NullableAuthoringInput, ValueExpression
from .visitors import (
    ExpressionVisitor,
    rewrite_expression,
    visit_expression,
    walk_expression,
)

__all__ = [
    "PRESERVE_ROWS",
    "ArrayExpression",
    "ArraySelection",
    "BoolExpression",
    "CustomDataTypeExpression",
    "Expression",
    "ExpressionNode",
    "ExpressionVisitor",
    "FieldReferenceExpression",
    "FloatExpression",
    "IntExpression",
    "LiteralExpression",
    "NullableAuthoringInput",
    "NullableDataType",
    "NullableExpression",
    "NullableSelection",
    "NumberExpression",
    "OperationExpression",
    "OperationParameter",
    "RowEffect",
    "RowSemantics",
    "SelectionDataType",
    "SelectionStructured",
    "SelectionUnit",
    "StrExpression",
    "StructExpression",
    "StructSelection",
    "Traversal",
    "ValueExpression",
    "ValueInput",
    "ValueSelection",
    "VariableExpression",
    "all_of",
    "any_of",
    "as_expression",
    "decode_expression",
    "decode_expression_ir",
    "encode_expression",
    "encode_expression_ir",
    "expression_to_ir",
    "field_reference",
    "literal",
    "operation",
    "rewrite_expression",
    "row_effects",
    "row_semantics",
    "select_expression",
    "select_member",
    "value_expression",
    "visit_expression",
    "walk_expression",
    "walk_expression_ir",
    "with_arguments",
    "wrap_expression",
]
