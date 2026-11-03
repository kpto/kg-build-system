"""The row-producing array expansion operation."""
from __future__ import annotations

import json
from hashlib import sha256

from ...model import FieldReferenceExpression, OperationExpression
from ...._private.semantics import row_effects
from .......kernel.internal.types import ArrayType, non_nullable
from ._predicates import is_array
from .spec import ArgumentSpec, OperationSpec, RowEffectSpec


def _scope(expression) -> tuple[str, ...]:
    if isinstance(expression, FieldReferenceExpression):
        return (expression.source, *expression.path)
    if isinstance(expression, OperationExpression):
        if (
            expression.operator == "struct_field"
            and len(expression.arguments) == 1
            and isinstance(expression.arguments[0], OperationExpression)
            and expression.arguments[0].operator == "expand"
        ):
            name = next(
                (item.value for item in expression.parameters if item.name == "name"),
                None,
            )
            parent_effects = row_effects(expression.arguments[0].row_semantics)
            if (
                isinstance(name, str)
                and name
                and parent_effects
                and parent_effects[-1].mode == "expand"
            ):
                return (*parent_effects[-1].scope, name)
        if expression.operator == "expand":
            effects = row_effects(expression.row_semantics)
            if effects and effects[-1].mode == "expand":
                return effects[-1].scope
    from ...dto.codec import expression_to_document
    from ...._private.dto import expression_dto

    encoded = json.dumps(
        expression_to_document(expression_dto(expression)),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return ("expression", sha256(encoded).hexdigest())


def _scope_of(nodes, types, parameters):
    return _scope(nodes[0])


def _result(types, parameters):
    array = non_nullable(types[0])
    assert isinstance(array, ArrayType)
    return array.item


EXPAND = OperationSpec(
    name="expand",
    arity=1,
    arguments=(ArgumentSpec(accepts=is_array, description="array value"),),
    result_type=_result,
    row_effect=RowEffectSpec("expand", scope=_scope_of),
)


__all__ = ["EXPAND"]
