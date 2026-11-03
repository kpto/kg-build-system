"""The expression blueprint DTOs and their document codec."""
from __future__ import annotations

from .blueprint_dto import (
    ExpressionDTO, ExpressionDTOBase, FieldReferenceDTO, LiteralExpressionDTO,
    OperationExpressionDTO, OperationParameterDTO, VariableExpressionDTO,
)
from .codec import expression_from_document, expression_to_document


def walk_expression_dto(expression: ExpressionDTO):
    """Yield an expression DTO tree in deterministic pre-order.

    Example:
        ```python
        from kg_build_system.declaration.foundations.expressions.internal import (
            LiteralExpressionDTO, walk_expression_dto,
        )
        from kg_build_system.kernel.internal.types.dto import UnitTypeDTO

        node = LiteralExpressionDTO(logical_type=UnitTypeDTO("int"), value=1)
        assert tuple(walk_expression_dto(node)) == (node,)
        ```
    """
    from ..._private.dto import walk_expression_dto as walk

    return walk(expression)


__all__ = [
    "ExpressionDTO", "ExpressionDTOBase", "FieldReferenceDTO",
    "LiteralExpressionDTO", "OperationExpressionDTO", "OperationParameterDTO",
    "VariableExpressionDTO", "expression_from_document",
    "expression_to_document", "walk_expression_dto",
]
