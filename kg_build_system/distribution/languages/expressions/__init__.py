"""Author-facing typed selections and bindable expressions.

Example:
    ```python
    from kg_build_system import value_expression
    from kg_build_system.distribution.languages.expressions import ValueExpression

    assert isinstance(value_expression(1), ValueExpression)
    ```
"""
from __future__ import annotations

from .model.public import (
    ArrayExpression, ArrayRowEffects, ArraySelection, BoolExpression,
    CustomDataTypeExpression, FloatExpression, IntExpression,
    NullableArrayRowEffects, NullableAuthoringInput, NullableDataType,
    NullableExpression, NullableRowEffects, NullableSelection, NumberExpression,
    RowEffects, SelectionDataType, SelectionStructured, SelectionUnit,
    StrExpression, StructExpression, StructSelection, ValueExpression, ValueInput,
    ValueSelection,
)
from .service.public import (
    all_of, any_of, as_expression, literal, select_expression, select_member,
    value_expression, wrap_expression,
)

__all__ = [
    "ArrayExpression", "ArrayRowEffects", "ArraySelection", "BoolExpression",
    "CustomDataTypeExpression", "FloatExpression", "IntExpression",
    "NullableArrayRowEffects", "NullableAuthoringInput", "NullableDataType",
    "NullableExpression", "NullableRowEffects", "NullableSelection",
    "NumberExpression", "RowEffects", "SelectionDataType", "SelectionStructured",
    "SelectionUnit", "StrExpression",
    "StructExpression", "StructSelection", "ValueExpression", "ValueInput",
    "ValueSelection", "all_of", "any_of", "as_expression", "literal",
    "select_expression", "select_member", "value_expression", "wrap_expression",
]
