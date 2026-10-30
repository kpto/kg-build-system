"""Text expression operators."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..nodes import SqlNode

from .....expressions.ir import OperationExpressionIR
from .....types.ir import NullableTypeIR, UnitTypeIR
from ....protocols import LoweringContext, Operand
from .base import require_arity


@dataclass(frozen=True, slots=True)
class Concat:
    operator = "concat"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        return exp.Anonymous(
            this="concat", expressions=[operand.sql() for operand in operands],
        )


@dataclass(frozen=True, slots=True)
class Replace:
    operator = "replace"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        require_arity(expression, operands, 3, "replace requires three arguments")
        return exp.Anonymous(
            this="replace", expressions=[operand.sql() for operand in operands],
        )


@dataclass(frozen=True, slots=True)
class ToString:
    operator = "to_string"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        require_arity(expression, operands, 1, "to_string requires one argument")
        source_type = operands[0].logical_type
        base = (
            source_type.value
            if isinstance(source_type, NullableTypeIR)
            else source_type
        )
        rendered = exp.Cast(
            this=operands[0].sql(), to=exp.DataType.build("VARCHAR"),
        )
        if isinstance(base, UnitTypeIR) and base.name == "timestamp":
            return exp.Anonymous(
                this="replace",
                expressions=[
                    rendered,
                    exp.Literal.string(" "),
                    exp.Literal.string("T"),
                ],
            )
        return rendered


def _split(text: SqlNode, separator: SqlNode) -> SqlNode:
    return exp.Anonymous(
        this="string_split",
        expressions=[text.copy(), separator.copy()],
    )


def _separator_parameters(
    expression: OperationExpressionIR,
    operands: Sequence[Operand[SqlNode]],
    context: LoweringContext[SqlNode],
) -> tuple[SqlNode, SqlNode, int, bool]:
    require_arity(
        expression, operands, 2, f"{expression.operator} requires two arguments",
    )
    occurrence = context.parameter(expression, "occurrence")
    include_separator = context.parameter(expression, "include_separator")
    if not isinstance(occurrence, int) or occurrence < 1:
        raise ValueError(
            f"{expression.operator} occurrence must be a positive integer"
        )
    if not isinstance(include_separator, bool):
        raise ValueError(
            f"{expression.operator} include_separator must be a Boolean"
        )
    return operands[0].sql(), operands[1].sql(), occurrence, include_separator


@dataclass(frozen=True, slots=True)
class BeforeSeparator:
    operator = "before_separator"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        text, separator, occurrence, include_separator = _separator_parameters(
            expression, operands, context,
        )
        sliced = exp.Anonymous(
            this="list_slice",
            expressions=[
                _split(text, separator),
                exp.Literal.number(1),
                exp.Literal.number(occurrence),
            ],
        )
        base = exp.Anonymous(
            this="array_to_string",
            expressions=[sliced, separator.copy()],
        )
        if not include_separator:
            return base
        present = exp.GT(
            this=exp.Anonymous(this="len", expressions=[_split(text, separator)]),
            expression=exp.Literal.number(occurrence),
        )
        suffix = exp.Case(
            ifs=[exp.If(this=present, true=separator.copy())],
            default=exp.Literal.string(""),
        )
        return exp.Anonymous(this="concat", expressions=[base, suffix])


@dataclass(frozen=True, slots=True)
class AfterSeparator:
    operator = "after_separator"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        text, separator, occurrence, include_separator = _separator_parameters(
            expression, operands, context,
        )
        sliced = exp.Anonymous(
            this="list_slice",
            expressions=[
                _split(text, separator),
                exp.Literal.number(occurrence + 1),
                exp.Literal.number(-1),
            ],
        )
        base = exp.Anonymous(
            this="array_to_string",
            expressions=[sliced, separator.copy()],
        )
        if not include_separator:
            return base
        present = exp.GT(
            this=exp.Anonymous(this="len", expressions=[_split(text, separator)]),
            expression=exp.Literal.number(occurrence),
        )
        joined = exp.Anonymous(
            this="concat", expressions=[separator.copy(), base],
        )
        return exp.Case(
            ifs=[exp.If(this=present, true=joined)],
            default=exp.Literal.string(""),
        )


OPERATORS = (Concat(), Replace(), ToString(), BeforeSeparator(), AfterSeparator())

__all__ = ["OPERATORS"]
