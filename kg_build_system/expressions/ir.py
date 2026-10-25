"""Compilation-only IR for expression trees."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, TypeAlias

from ..types.ir import LogicalTypeIR
from .._frozen_json import FrozenJson


@dataclass(frozen=True, slots=True, kw_only=True)
class ExpressionIRBase:
    logical_type: LogicalTypeIR


@dataclass(frozen=True, slots=True, kw_only=True)
class LiteralExpressionIR(ExpressionIRBase):
    value: FrozenJson


@dataclass(frozen=True, slots=True, kw_only=True)
class VariableExpressionIR(ExpressionIRBase):
    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldReferenceExpressionIR(ExpressionIRBase):
    source: str
    path: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OperationParameterIR:
    name: str
    value: FrozenJson


@dataclass(frozen=True, slots=True, kw_only=True)
class OperationExpressionIR(ExpressionIRBase):
    operator: str
    arguments: tuple["ExpressionIR", ...]
    parameters: tuple[OperationParameterIR, ...] = ()


ExpressionIR: TypeAlias = (
    LiteralExpressionIR | VariableExpressionIR | FieldReferenceExpressionIR
    | OperationExpressionIR
)


def walk_expression_ir(expression: ExpressionIR) -> Iterator[ExpressionIR]:
    yield expression
    if isinstance(expression, OperationExpressionIR):
        for argument in expression.arguments:
            yield from walk_expression_ir(argument)


__all__ = [
    "ExpressionIR", "ExpressionIRBase", "FieldReferenceExpressionIR",
    "LiteralExpressionIR", "OperationExpressionIR", "OperationParameterIR",
    "VariableExpressionIR", "walk_expression_ir",
]
