"""Mappings from expression domain models to compilation DTOs."""
from __future__ import annotations

from . import ir
from . import dto
from ..types.mapping import type_to_dto


def expression_to_dto(value: ir.ExpressionNode) -> dto.ExpressionDTO:
    rows = dto.RowSemanticsDTO(tuple(
        dto.RowEffectDTO(effect.mode, effect.scope)
        for effect in value.row_semantics.effects
    ))
    common = {"logical_type": type_to_dto(value.logical_type), "row_semantics": rows}
    if isinstance(value, ir.LiteralExpression):
        return dto.LiteralExpressionDTO(value=value.value, **common)
    if isinstance(value, ir.FieldReferenceExpression):
        return dto.FieldReferenceExpressionDTO(
            source=value.source,
            path=value.path,
            traversals=tuple(dto.TraversalDTO(item.kind, item.path) for item in value.traversals),
            **common,
        )
    if isinstance(value, ir.OperationExpression):
        return dto.OperationExpressionDTO(
            operator=value.operator,
            arguments=tuple(expression_to_dto(argument) for argument in value.arguments),
            parameters=tuple(dto.OperationParameterDTO(item.name, item.value) for item in value.parameters),
            **common,
        )
    raise TypeError(f"unsupported expression domain model {value!r}")


__all__ = ["expression_to_dto"]
