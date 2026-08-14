"""Compilation-only IR for expression trees."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Literal, TypeAlias

from ..types.ir import LogicalTypeIR
from .._frozen_json import FrozenJson


@dataclass(frozen=True, slots=True)
class RowEffectIR:
    mode: Literal["expand", "filter"]
    scope: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RowSemanticsIR:
    effects: tuple[RowEffectIR, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ExpressionIRBase:
    logical_type: LogicalTypeIR
    row_semantics: RowSemanticsIR = RowSemanticsIR()


@dataclass(frozen=True, slots=True, kw_only=True)
class LiteralExpressionIR(ExpressionIRBase):
    value: FrozenJson


@dataclass(frozen=True, slots=True)
class TraversalIR:
    kind: Literal["struct", "array"]
    path: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldReferenceExpressionIR(ExpressionIRBase):
    source: str
    path: tuple[str, ...]
    traversals: tuple[TraversalIR, ...] = ()


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
    LiteralExpressionIR | FieldReferenceExpressionIR | OperationExpressionIR
)


def walk_expression_ir(expression: ExpressionIR) -> Iterator[ExpressionIR]:
    yield expression
    if isinstance(expression, OperationExpressionIR):
        for argument in expression.arguments:
            yield from walk_expression_ir(argument)


__all__ = [
    "ExpressionIR", "ExpressionIRBase", "FieldReferenceExpressionIR",
    "LiteralExpressionIR", "OperationExpressionIR", "OperationParameterIR",
    "RowEffectIR", "RowSemanticsIR", "TraversalIR", "walk_expression_ir",
]
