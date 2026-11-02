"""Compilation IR for expression trees.

This surface holds only frozen DTOs and the traversal over them. It stores an
operator name, arguments, parameters and a logical type; it knows no concrete
operator.
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TypeAlias

from ..._frozen_json import FrozenJson
from ...types.internal.ir import LogicalTypeIR


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
    """Yield an expression IR tree in deterministic pre-order."""
    yield expression
    if isinstance(expression, OperationExpressionIR):
        for argument in expression.arguments:
            yield from walk_expression_ir(argument)


__all__ = [
    "ExpressionIR", "ExpressionIRBase", "FieldReferenceExpressionIR",
    "LiteralExpressionIR", "OperationExpressionIR", "OperationParameterIR",
    "VariableExpressionIR", "walk_expression_ir",
]
