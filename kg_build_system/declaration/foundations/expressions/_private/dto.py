"""Map the authoring expression model to the expression blueprint DTO."""
from __future__ import annotations

from collections.abc import Iterator

from kg_build_system.kernel.internal.types import type_to_dto

from ..internal.dto.blueprint_dto import (
    ExpressionDTO, FieldReferenceDTO, LiteralExpressionDTO,
    OperationExpressionDTO, OperationParameterDTO, VariableExpressionDTO,
)
from ..internal.model import (
    ExpressionNode, FieldReferenceExpression, LiteralExpression,
    OperationExpression, VariableExpression,
)


def expression_dto(value: ExpressionNode) -> ExpressionDTO:
    """Return the blueprint DTO of one authoring expression node."""
    common = {"logical_type": type_to_dto(value.logical_type)}
    if isinstance(value, LiteralExpression):
        return LiteralExpressionDTO(value=value.value, **common)
    if isinstance(value, VariableExpression):
        return VariableExpressionDTO(name=value.name, **common)
    if isinstance(value, FieldReferenceExpression):
        return FieldReferenceDTO(
            source=value.source,
            path=value.path,
            **common,
        )
    if isinstance(value, OperationExpression):
        return OperationExpressionDTO(
            operator=value.operator,
            arguments=tuple(expression_dto(argument) for argument in value.arguments),
            parameters=tuple(
                OperationParameterDTO(item.name, item.value)
                for item in value.parameters
            ),
            **common,
        )
    raise TypeError(f"unsupported expression model {value!r}")


def walk_expression_dto(expression: ExpressionDTO) -> Iterator[ExpressionDTO]:
    """Yield an expression DTO tree in deterministic pre-order."""
    yield expression
    if isinstance(expression, OperationExpressionDTO):
        for argument in expression.arguments:
            yield from walk_expression_dto(argument)


__all__ = ["expression_dto", "walk_expression_dto"]
