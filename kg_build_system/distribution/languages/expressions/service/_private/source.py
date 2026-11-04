"""Render expression DTOs back to inline authoring source."""
from __future__ import annotations

from typing import Any

from kg_build_system.kernel.model.internal.json import FrozenObject, thaw_json
from kg_build_system.kernel.model.internal.types.dto import ArrayTypeDTO, CustomTypeDTO, LogicalTypeDTO, NullableTypeDTO, StructTypeDTO, UnitTypeDTO

from kg_build_system.kernel import SourceFragment
from ...model.internal.dto.blueprint_dto import (
    ExpressionDTO, FieldReferenceDTO, LiteralExpressionDTO,
    OperationExpressionDTO, VariableExpressionDTO,
)

UNIT_NAMES = {
    "bool": "BOOL",
    "int": "INT",
    "float": "FLOAT",
    "str": "STR",
    "date": "DATE",
    "time": "TIME",
    "timestamp": "TIMESTAMP",
    "uuid": "UUID",
}


def render_type(logical_type: LogicalTypeDTO) -> str:
    if isinstance(logical_type, UnitTypeDTO):
        return UNIT_NAMES[logical_type.name]
    if isinstance(logical_type, CustomTypeDTO):
        return f"CustomType({logical_type.module!r}, {logical_type.qualname!r})"
    if isinstance(logical_type, StructTypeDTO):
        return f"StructType({logical_type.module!r}, {logical_type.qualname!r})"
    if isinstance(logical_type, ArrayTypeDTO):
        return f"ArrayType({render_type(logical_type.item)})"
    if isinstance(logical_type, NullableTypeDTO):
        return f"NullableType({render_type(logical_type.value)})"
    raise TypeError(f"unsupported logical type {logical_type!r}")


def render_value(value: Any) -> str:
    if isinstance(value, FrozenObject):
        items = ", ".join(
            f"{key!r}: {render_value(thaw_json(item))}"
            for key, item in value.items
        )
        return "{" + items + "}"
    if isinstance(value, tuple):
        return "[" + ", ".join(render_value(item) for item in value) + "]"
    return repr(value)


def render(expression: ExpressionDTO) -> str:
    if isinstance(expression, LiteralExpressionDTO):
        return (
            "value_expression("
            f"{render_value(expression.value)}, "
            f"logical_type={render_type(expression.logical_type)})"
        )
    if isinstance(expression, VariableExpressionDTO):
        return expression.name
    if isinstance(expression, FieldReferenceDTO):
        path = ", ".join(
            repr(part)
            for part in (expression.field.field, *expression.path)
        )
        return (
            "field_reference("
            f"source={expression.field.relation!r}, path=({path},), "
            f"logical_type={render_type(expression.logical_type)})"
        )
    if isinstance(expression, OperationExpressionDTO):
        arguments = ", ".join(render(argument) for argument in expression.arguments)
        parameters = "".join(
            f", {parameter.name}={render_value(parameter.value)}"
            for parameter in expression.parameters
        )
        return (
            f"operation({expression.operator.name!r}, {arguments}"
            f"{parameters}, logical_type={render_type(expression.logical_type)})"
        )
    raise TypeError(f"unsupported expression DTO {expression!r}")


def render_expression_source(dto: ExpressionDTO) -> SourceFragment:
    """Render one expression DTO as an inline authoring expression."""
    return SourceFragment(
        "inline",
        render(dto),
        (
            "from kg_build_system import value_expression",
            "from kg_build_system.distribution.languages.expressions.service.internal import "
            "field_reference, operation",
            "from kg_build_system import "
            "ArrayType, NullableType, "
            "BOOL, DATE, FLOAT, INT, STR, TIME, TIMESTAMP, UUID",
            "from kg_build_system.kernel.model.public.types import "
            "CustomType, StructType",
        ),
    )


__all__ = ["render_expression_source"]
