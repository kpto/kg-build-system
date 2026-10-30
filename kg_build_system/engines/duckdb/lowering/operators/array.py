"""Array expression operators."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlglot import exp

from ..nodes import SqlNode

from .....expressions.ir import OperationExpressionIR
from ....protocols import LoweringContext, Operand
from .base import require_arity


@dataclass(frozen=True, slots=True)
class ArrayAt:
    operator = "array_at"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        require_arity(
            expression, operands, 2, "array_at requires an array and an index",
        )
        return exp.Anonymous(
            this="list_extract",
            expressions=[
                operands[0].sql(),
                exp.Add(
                    this=operands[1].sql(), expression=exp.Literal.number(1),
                ),
            ],
        )


@dataclass(frozen=True, slots=True)
class ArraySlice:
    operator = "array_slice"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        require_arity(
            expression, operands, 3,
            "array_slice requires an array, a start and an end",
        )
        return exp.Anonymous(
            this="list_slice",
            expressions=[
                operands[0].sql(),
                exp.Add(
                    this=operands[1].sql(), expression=exp.Literal.number(1),
                ),
                operands[2].sql(),
            ],
        )


@dataclass(frozen=True, slots=True)
class TransformItems:
    operator = "transform_items"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        require_arity(
            expression, operands, 2, "transform_items requires two arguments",
        )
        item = exp.column("_kg_item", quoted=False)
        item_name = context.parameter(expression, "item")
        body = context.with_variable(item_name, item).lower(
            expression.arguments[1]
        )
        return exp.Anonymous(
            this="list_transform",
            expressions=[
                operands[0].sql(),
                exp.Lambda(this=body, expressions=[item.copy()]),
            ],
        )


@dataclass(frozen=True, slots=True)
class DropNullItems:
    operator = "drop_null_items"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        require_arity(
            expression, operands, 1, "drop_null_items requires one argument",
        )
        item = exp.column("_kg_item", quoted=False)
        return exp.Anonymous(
            this="list_filter",
            expressions=[
                operands[0].sql(),
                exp.Lambda(
                    this=exp.Not(this=exp.Is(
                        this=item.copy(), expression=exp.null(),
                    )),
                    expressions=[item],
                ),
            ],
        )


@dataclass(frozen=True, slots=True)
class Sort:
    operator = "sort"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        require_arity(expression, operands, 1, "sort requires one argument")
        return exp.Anonymous(this="list_sort", expressions=[operands[0].sql()])


@dataclass(frozen=True, slots=True)
class Distinct:
    operator = "distinct"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        require_arity(expression, operands, 1, "distinct requires one argument")
        return exp.Anonymous(this="list_distinct", expressions=[operands[0].sql()])


@dataclass(frozen=True, slots=True)
class ArrayJoin:
    operator = "join"

    def lower(
        self,
        expression: OperationExpressionIR,
        operands: Sequence[Operand[SqlNode]],
        context: LoweringContext[SqlNode],
    ) -> SqlNode:
        require_arity(
            expression, operands, 2, "join requires an array and a separator",
        )
        return exp.Anonymous(
            this="array_to_string",
            expressions=[operands[0].sql(), operands[1].sql()],
        )


OPERATORS = (
    ArrayAt(),
    ArraySlice(),
    TransformItems(),
    DropNullItems(),
    Sort(),
    Distinct(),
    ArrayJoin(),
)

__all__ = ["OPERATORS"]
