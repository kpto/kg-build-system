"""Expression planning facts the DuckDB emitter needs.

Only expansion scopes are shared with the emitter: an explicit ``expand``
operation has one stable, plan-local identity, and the row-source and operator
emitters must derive the same identity without importing the compiler.
"""
from __future__ import annotations

import json
from hashlib import sha256

from kg_build_system.distribution.languages.expressions.model.internal import (
    ExpressionDTO,
    FieldReferenceDTO,
    OperationExpressionDTO,
)
from kg_build_system.distribution.languages.expressions.service.internal import (
    expression_to_document,
)


def _key(expression: ExpressionDTO) -> str:
    return json.dumps(
        expression_to_document(expression),
        sort_keys=True,
        separators=(",", ":"),
    )


def expansion_scope(expression: OperationExpressionDTO) -> tuple[str, ...]:
    """Derive a stable, plan-local identity for one explicit ``expand`` operation."""
    if expression.operator.name != "expand":
        raise ValueError("expansion scopes can only be derived for expand operations")
    if len(expression.arguments) != 1:
        raise ValueError("expand requires one argument")
    argument = expression.arguments[0]
    if isinstance(argument, FieldReferenceDTO):
        return (
            argument.field.relation, argument.field.field, *argument.path,
        )
    if (
        isinstance(argument, OperationExpressionDTO)
        and argument.operator.name == "struct_field"
        and len(argument.arguments) == 1
        and isinstance(argument.arguments[0], OperationExpressionDTO)
        and argument.arguments[0].operator.name == "expand"
    ):
        name = next(
            (
                parameter.value
                for parameter in argument.parameters
                if parameter.name == "name"
            ),
            None,
        )
        if isinstance(name, str) and name:
            return (*expansion_scope(argument.arguments[0]), name)
    return ("expression", sha256(_key(expression).encode("utf-8")).hexdigest())


__all__ = ["expansion_scope"]
