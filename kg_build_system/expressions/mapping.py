"""Mappings from expression domain models to compilation IRs."""
from __future__ import annotations

from . import ir, models
from ..types.mapping import type_to_ir


def expression_to_ir(value: models.ExpressionNode) -> ir.ExpressionIR:
    common = {"logical_type": type_to_ir(value.logical_type)}
    if isinstance(value, models.LiteralExpression):
        return ir.LiteralExpressionIR(value=value.value, **common)
    if isinstance(value, models.VariableExpression):
        return ir.VariableExpressionIR(name=value.name, **common)
    if isinstance(value, models.FieldReferenceExpression):
        return ir.FieldReferenceExpressionIR(
            source=value.source,
            path=value.path,
            **common,
        )
    if isinstance(value, models.OperationExpression):
        return ir.OperationExpressionIR(
            operator=value.operator,
            arguments=tuple(expression_to_ir(argument) for argument in value.arguments),
            parameters=tuple(ir.OperationParameterIR(item.name, item.value) for item in value.parameters),
            **common,
        )
    raise TypeError(f"unsupported expression domain model {value!r}")


__all__ = ["expression_to_ir"]
