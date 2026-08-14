"""Compilation-only transfer objects for expression trees."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Literal, TypeAlias

from ..types.dto import LogicalTypeDTO
from .._frozen_json import FrozenJson


@dataclass(frozen=True, slots=True)
class RowEffectDTO:
    mode: Literal["expand", "filter"]
    scope: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RowSemanticsDTO:
    effects: tuple[RowEffectDTO, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ExpressionDTOBase:
    logical_type: LogicalTypeDTO
    row_semantics: RowSemanticsDTO = RowSemanticsDTO()


@dataclass(frozen=True, slots=True, kw_only=True)
class LiteralExpressionDTO(ExpressionDTOBase):
    value: FrozenJson


@dataclass(frozen=True, slots=True)
class TraversalDTO:
    kind: Literal["struct", "array"]
    path: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldReferenceExpressionDTO(ExpressionDTOBase):
    source: str
    path: tuple[str, ...]
    traversals: tuple[TraversalDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class OperationParameterDTO:
    name: str
    value: FrozenJson


@dataclass(frozen=True, slots=True, kw_only=True)
class OperationExpressionDTO(ExpressionDTOBase):
    operator: str
    arguments: tuple["ExpressionDTO", ...]
    parameters: tuple[OperationParameterDTO, ...] = ()


ExpressionDTO: TypeAlias = (
    LiteralExpressionDTO | FieldReferenceExpressionDTO | OperationExpressionDTO
)


def walk_expression_dto(expression: ExpressionDTO) -> Iterator[ExpressionDTO]:
    yield expression
    if isinstance(expression, OperationExpressionDTO):
        for argument in expression.arguments:
            yield from walk_expression_dto(argument)


__all__ = [
    "ExpressionDTO", "ExpressionDTOBase", "FieldReferenceExpressionDTO",
    "LiteralExpressionDTO", "OperationExpressionDTO", "OperationParameterDTO",
    "RowEffectDTO", "RowSemanticsDTO", "TraversalDTO", "walk_expression_dto",
]
