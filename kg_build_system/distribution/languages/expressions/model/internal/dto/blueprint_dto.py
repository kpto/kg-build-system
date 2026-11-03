"""The expression's part of the graph blueprint.

The DTO records an operator name, its arguments, named parameters and the
logical type of the result. It knows no concrete operation and carries no
authoring row semantics; row effects are operations in the expression tree.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from kg_build_system.kernel.model.internal.json import FrozenJson
from kg_build_system.kernel.model.internal.types.dto import LogicalTypeDTO


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


__all__ = [
    "ExpressionDTO", "ExpressionDTOBase", "FieldReferenceDTO",
    "LiteralExpressionDTO", "OperationExpressionDTO", "OperationParameterDTO",
    "VariableExpressionDTO",
]
