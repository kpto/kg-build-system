"""Lower the ``before_separator`` expression operator."""
from __future__ import annotations

from typing import TYPE_CHECKING

from collections.abc import Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..sql import SqlNode

from .....expressions.internal.ir import OperationExpressionIR

if TYPE_CHECKING:
    from ....internal.protocols import LoweringContext, Operand
from .base import _separator_parameters, _split


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


__all__ = ["BeforeSeparator"]
