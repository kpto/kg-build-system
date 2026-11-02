"""Mapping from the domain expression model to the compilation IR."""
from __future__ import annotations

from ...types.internal import type_to_ir
from ..internal import ir
from ..internal import model as _model


def expression_to_ir(value: _model.ExpressionNode) -> ir.ExpressionIR:
    """Lower one domain expression to its compilation IR."""
    common = {"logical_type": type_to_ir(value.logical_type)}
    if isinstance(value, _model.LiteralExpression):
        return ir.LiteralExpressionIR(value=value.value, **common)
    if isinstance(value, _model.VariableExpression):
        return ir.VariableExpressionIR(name=value.name, **common)
    if isinstance(value, _model.FieldReferenceExpression):
        return ir.FieldReferenceExpressionIR(
            source=value.source,
            path=value.path,
            **common,
        )
    if isinstance(value, _model.OperationExpression):
        return ir.OperationExpressionIR(
            operator=value.operator,
            arguments=tuple(expression_to_ir(argument) for argument in value.arguments),
            parameters=tuple(
                ir.OperationParameterIR(item.name, item.value)
                for item in value.parameters
            ),
            **common,
        )
    raise TypeError(f"unsupported expression domain model {value!r}")


__all__ = ["expression_to_ir"]
