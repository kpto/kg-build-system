"""Lower the ``to_string`` expression operator."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..sql import SqlNode

from ....expressions.ir import OperationExpressionIR
from ....types.ir import NullableTypeIR, UnitTypeIR
from ...protocols import LoweringContext, Operand
from .base import require_arity


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


__all__ = ["ToString"]
