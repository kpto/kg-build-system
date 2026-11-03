"""The expression's part of the graph blueprint.

The DTO records an operator name, its arguments, named parameters and the
logical type of the result. It knows no concrete operation and carries no
authoring row semantics; row effects are operations in the expression tree.
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TypeAlias

from kg_build_system.kernel.internal.json import FrozenJson
from kg_build_system.kernel.internal.types.dto import LogicalTypeDTO


@dataclass(frozen=True, slots=True, kw_only=True)
class ExpressionDTOBase:
    """The logical type shared by every expression DTO."""

    logical_type: LogicalTypeDTO


@dataclass(frozen=True, slots=True, kw_only=True)
class LiteralExpressionDTO(ExpressionDTOBase):
    """A canonical literal value."""

    value: FrozenJson


@dataclass(frozen=True, slots=True, kw_only=True)
class VariableExpressionDTO(ExpressionDTOBase):
    """One bound variable inside a transform selector."""

    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldReferenceDTO(ExpressionDTOBase):
    """A read of one source field path."""

    source: str
    path: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OperationParameterDTO:
    """One named operation parameter."""

    name: str
    value: FrozenJson


@dataclass(frozen=True, slots=True, kw_only=True)
class OperationExpressionDTO(ExpressionDTOBase):
    """One operation applied to argument expressions."""

    operator: str
    arguments: tuple["ExpressionDTO", ...]
    parameters: tuple[OperationParameterDTO, ...] = ()


ExpressionDTO: TypeAlias = (
    LiteralExpressionDTO | VariableExpressionDTO | FieldReferenceDTO
    | OperationExpressionDTO
)


def walk_expression_dto(expression: ExpressionDTO) -> Iterator[ExpressionDTO]:
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
    yield expression
    if isinstance(expression, OperationExpressionDTO):
        for argument in expression.arguments:
            yield from walk_expression_dto(argument)


__all__ = [
    "ExpressionDTO", "ExpressionDTOBase", "FieldReferenceDTO",
    "LiteralExpressionDTO", "OperationExpressionDTO", "OperationParameterDTO",
    "VariableExpressionDTO", "walk_expression_dto",
]
