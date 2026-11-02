"""Framework-internal interface of the expression package.

Other subpackages import the domain expression model, operation specs, selection
construction helpers, codecs and visitors here. The author-facing surface is
:mod:`kg_build_system.expressions`; the compilation IR is
:mod:`kg_build_system.expressions.ir`.
"""
from __future__ import annotations

from ._build import field_reference, operation, with_arguments
from ._codec import decode_expression, encode_expression
from ._coercion import expression_input
from ._ir_codec import decode_expression_ir, encode_expression_ir
from ._literals import literal
from ._mapping import expression_to_ir
from ._model import (
    PRESERVE_ROWS, Expression, ExpressionNode, FieldReferenceExpression,
    LiteralExpression, OperationExpression, OperationParameter, RowEffect,
    RowSemantics, Traversal, VariableExpression,
)
from ._semantics import compose_row_semantics, row_effects, row_semantics
from ._visitors import (
    ExpressionVisitor, rewrite_expression, visit_expression, walk_expression,
)
from .arrays import ArrayExpression
from .boolean import BoolExpression, all_of, any_of
from .custom import CustomDataTypeExpression
from .factory import value_expression, wrap_expression
from .ir import (
    ExpressionIR, ExpressionIRBase, FieldReferenceExpressionIR,
    LiteralExpressionIR, OperationExpressionIR, OperationParameterIR,
    VariableExpressionIR, walk_expression_ir,
)
from .nullable import NullableExpression
from .numeric import FloatExpression, IntExpression, NumberExpression
from .operations import (
    DEFAULT_OPERATIONS, ArgumentSpec, OperationRegistry, OperationSpec,
    ParameterSpec, RowEffectSpec,
)
from .selections import (
    ArrayRowEffects, ArraySelection, NullableDataType, NullableRowEffects,
    NullableSelection, RowEffects, SelectionDataType, SelectionStructured,
    SelectionUnit, StructSelection, ValueInput, ValueSelection, as_expression,
    select_expression, select_member,
)
from .structs import StructExpression
from .text import StrExpression
from .values import NullableAuthoringInput, ValueExpression


__all__ = [
    "PRESERVE_ROWS", "ArgumentSpec", "ArrayExpression", "ArrayRowEffects",
    "ArraySelection", "BoolExpression", "CustomDataTypeExpression",
    "DEFAULT_OPERATIONS", "Expression", "ExpressionIR", "ExpressionIRBase",
    "ExpressionNode", "ExpressionVisitor", "FieldReferenceExpression",
    "FieldReferenceExpressionIR", "FloatExpression", "IntExpression",
    "LiteralExpression", "LiteralExpressionIR", "NullableAuthoringInput",
    "NullableDataType", "NullableExpression", "NullableRowEffects",
    "NullableSelection", "NumberExpression", "OperationExpression",
    "OperationExpressionIR", "OperationParameter", "OperationParameterIR",
    "OperationRegistry", "OperationSpec", "ParameterSpec", "RowEffect",
    "RowEffectSpec",
    "RowEffects", "RowSemantics", "SelectionDataType", "SelectionStructured",
    "SelectionUnit", "StrExpression", "StructExpression", "StructSelection",
    "Traversal", "ValueExpression", "ValueInput", "ValueSelection",
    "VariableExpression", "VariableExpressionIR", "all_of", "any_of",
    "as_expression", "compose_row_semantics", "decode_expression",
    "decode_expression_ir", "encode_expression", "encode_expression_ir",
    "expression_input", "expression_to_ir", "field_reference", "literal",
    "operation", "rewrite_expression", "row_effects", "row_semantics",
    "select_expression", "select_member", "value_expression",
    "visit_expression", "walk_expression", "walk_expression_ir",
    "with_arguments", "wrap_expression",
]
