"""Author-facing typed selections and bindable expressions.

A selection is a typed position in a row and owns null policy. An expression is
the bindable calculation behind it. This module composes the families an author
writes; the domain model, operation specs and codecs are in
:mod:`kg_build_system.expressions.interfaces`.
"""
from __future__ import annotations

from .arrays import ArrayExpression
from .boolean import BoolExpression
from .custom import CustomDataTypeExpression
from .interfaces import (
    all_of,
    any_of,
    as_expression,
    literal,
    select_expression,
    select_member,
    value_expression,
    wrap_expression,
)
from .nullable import NullableExpression
from .numeric import FloatExpression, IntExpression, NumberExpression
from .selections import (
    ArrayRowEffects,
    ArraySelection,
    NullableDataType,
    NullableRowEffects,
    NullableSelection,
    RowEffects,
    SelectionDataType,
    SelectionStructured,
    SelectionUnit,
    StructSelection,
    ValueInput,
    ValueSelection,
)
from .structs import StructExpression
from .text import StrExpression
from .values import NullableAuthoringInput, ValueExpression


__all__ = [
    "ArrayExpression",
    "ArrayRowEffects",
    "ArraySelection",
    "BoolExpression",
    "CustomDataTypeExpression",
    "FloatExpression",
    "IntExpression",
    "NullableAuthoringInput",
    "NullableDataType",
    "NullableExpression",
    "NullableRowEffects",
    "NullableSelection",
    "NumberExpression",
    "RowEffects",
    "SelectionDataType",
    "SelectionStructured",
    "SelectionUnit",
    "StrExpression",
    "StructExpression",
    "StructSelection",
    "ValueExpression",
    "ValueInput",
    "ValueSelection",
    "all_of",
    "any_of",
    "as_expression",
    "literal",
    "select_expression",
    "select_member",
    "value_expression",
    "wrap_expression",
]
