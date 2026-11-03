"""Render expression DTOs back to inline authoring source."""
from __future__ import annotations

from typing import Any

from kg_build_system.kernel.internal.json import FrozenObject, thaw_json
from kg_build_system.kernel.internal.types.dto import (
    ArrayTypeDTO, CustomTypeDTO, LogicalTypeDTO, NullableTypeDTO, StructTypeDTO,
    UnitTypeDTO,
)

from ....source import SourceFragment
from ..dto.blueprint_dto import (
    ExpressionDTO, FieldReferenceDTO, LiteralExpressionDTO,
    OperationExpressionDTO, VariableExpressionDTO,
)

_UNIT_NAMES = {
    "bool": "BOOL",
    "int": "INT",
    "float": "FLOAT",
    "str": "STR",
    "date": "DATE",
    "time": "TIME",
    "timestamp": "TIMESTAMP",
    "uuid": "UUID",
}


def _render_type(logical_type: LogicalTypeDTO) -> str:
    if isinstance(logical_type, UnitTypeDTO):
        return _UNIT_NAMES[logical_type.name]
    if isinstance(logical_type, CustomTypeDTO):
        return f"CustomType({logical_type.module!r}, {logical_type.qualname!r})"
    if isinstance(logical_type, StructTypeDTO):
        return f"StructType({logical_type.module!r}, {logical_type.qualname!r})"
    if isinstance(logical_type, ArrayTypeDTO):
        return f"ArrayType({_render_type(logical_type.item)})"
    if isinstance(logical_type, NullableTypeDTO):
        return f"NullableType({_render_type(logical_type.value)})"
    raise TypeError(f"unsupported logical type {logical_type!r}")


def _render_value(value: Any) -> str:
    if isinstance(value, FrozenObject):
        items = ", ".join(
            f"{key!r}: {_render_value(thaw_json(item))}"
            for key, item in value.items
        )
        return "{" + items + "}"
    if isinstance(value, tuple):
        return "[" + ", ".join(_render_value(item) for item in value) + "]"
    return repr(value)


def _render(expression: ExpressionDTO) -> str:
    if isinstance(expression, LiteralExpressionDTO):
        return (
            "value_expression("
            f"{_render_value(expression.value)}, "
            f"logical_type={_render_type(expression.logical_type)})"
        )
    if isinstance(expression, VariableExpressionDTO):
        return expression.name
    if isinstance(expression, FieldReferenceDTO):
        path = ", ".join(repr(part) for part in expression.path)
        return (
            "field_reference("
            f"source={expression.source!r}, path=({path},), "
            f"logical_type={_render_type(expression.logical_type)})"
        )
    if isinstance(expression, OperationExpressionDTO):
        arguments = ", ".join(_render(argument) for argument in expression.arguments)
        parameters = "".join(
            f", {parameter.name}={_render_value(parameter.value)}"
            for parameter in expression.parameters
        )
        return (
            f"operation({expression.operator!r}, {arguments}"
            f"{parameters}, logical_type={_render_type(expression.logical_type)})"
        )
    raise TypeError(f"unsupported expression DTO {expression!r}")


def render_expression_source(dto: ExpressionDTO) -> SourceFragment:
    """Render one expression DTO as an inline authoring expression.

    Example:
        ```python
        from kg_build_system.declaration.foundations.expressions.internal import (
            LiteralExpressionDTO, render_expression_source,
        )
        from kg_build_system.kernel.internal.types.dto import UnitTypeDTO

        node = LiteralExpressionDTO(logical_type=UnitTypeDTO("int"), value=1)
        assert render_expression_source(node).text.startswith("value_expression(")
        ```
    """
    return SourceFragment(
        text=_render(dto),
        imports=(
            "from kg_build_system import value_expression",
            "from kg_build_system.declaration.foundations.expressions.internal import "
            "field_reference, operation",
            "from kg_build_system.types import "
            "ArrayType, NullableType, "
            "BOOL, DATE, FLOAT, INT, STR, TIME, TIMESTAMP, UUID",
            "from kg_build_system.types import CustomType, StructType",
        ),
    )


__all__ = ["render_expression_source"]
