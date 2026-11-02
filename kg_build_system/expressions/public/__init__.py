"""Author-facing expressions and selections.

This package contains only the names a graph author writes: expression
families, selection families, row-effect handles and the construction helpers
that preserve the type of their input.

Example:
    ```python
    from kg_build_system import Field, Table, field
    from kg_build_system.expressions import ValueSelection

    class Row(Table):
        name: Field[str] = field(name="name")

    assert isinstance(Row.name, ValueSelection)
    ```
"""
from __future__ import annotations

from .arrays import ArrayExpression
from .boolean import BoolExpression, all_of, any_of
from .custom import CustomDataTypeExpression
from .factory import literal, value_expression, wrap_expression
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
    as_expression,
    select_expression,
    select_member,
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
