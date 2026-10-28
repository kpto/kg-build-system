"""Compose expression row semantics into an engine-neutral relational plan."""
from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256

from ..expressions.ir import (
    ExpressionIR as ExpressionNode,
    FieldReferenceExpressionIR as FieldReferenceExpression,
    OperationExpressionIR as OperationExpression,
    walk_expression_ir as walk_expression,
)
from ..expressions.ir_codec import encode_expression_ir as encode_expression
from ..expressions.models import ExpressionNode as DomainExpressionNode
from ..expressions.mapping import expression_to_ir
from .ir import (
    ExpandIR as Expand, FilterIR as Filter, RelationPlanIR as RelationPlan,
    ScanIR as Scan,
)


def _key(expression: ExpressionNode) -> str:
    return json.dumps(
        encode_expression(expression), sort_keys=True, separators=(",", ":"),
    )


def expansion_scope(expression: OperationExpression) -> tuple[str, ...]:
    """Derive a stable, plan-local identity for one explicit ``expand`` operation."""
    if expression.operator != "expand":
        raise ValueError("expansion scopes can only be derived for expand operations")
    if len(expression.arguments) != 1:
        raise ValueError("expand requires one argument")
    argument = expression.arguments[0]
    if isinstance(argument, FieldReferenceExpression):
        return (argument.source, *argument.path)
    if (
        isinstance(argument, OperationExpression)
        and argument.operator == "struct_field"
        and len(argument.arguments) == 1
        and isinstance(argument.arguments[0], OperationExpression)
        and argument.arguments[0].operator == "expand"
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


def _operators_post_order(expression: ExpressionNode):
    if not isinstance(expression, OperationExpression):
        return
    for argument in expression.arguments:
        yield from _operators_post_order(argument)
    yield expression


def lower_product(
    outputs: Mapping[str, ExpressionNode | DomainExpressionNode],
    relations: Mapping[str, str],
    *,
    predicates: tuple[ExpressionNode, ...] = (),
) -> RelationPlan:
    """Plan one projection or binding without leaking its row effects elsewhere."""
    if not outputs:
        raise ValueError("relational products require at least one output")
    compiled_outputs = {
        name: expression_to_ir(expression)
        if isinstance(expression, DomainExpressionNode)
        else expression
        for name, expression in outputs.items()
    }
    referenced = sorted({
        node.source
        for expression in (*compiled_outputs.values(), *predicates)
        for node in walk_expression(expression)
        if isinstance(node, FieldReferenceExpression)
    })
    missing = set(referenced) - set(relations)
    if missing:
        raise ValueError("no materialised relation for: " + ", ".join(sorted(missing)))
    if len(referenced) > 1:
        raise ValueError(
            "a relational product requires one driving source; additional sources "
            "must be introduced by an explicit lookup"
        )
    scans = tuple(Scan(source, relations[source], f"t{index}") for index, source in enumerate(referenced))

    expands: list[Expand] = []
    filters: list[Filter] = []
    expansion_scopes: set[tuple[str, ...]] = set()
    filter_keys: set[str] = set()
    for expression in compiled_outputs.values():
        for operation in _operators_post_order(expression):
            if operation.operator == "expand":
                if len(operation.arguments) != 1:
                    raise ValueError("expand requires one argument")
                scope = expansion_scope(operation)
                if scope not in expansion_scopes:
                    expansion_scopes.add(scope)
                    expands.append(Expand(scope, operation.arguments[0], f"expanded{len(expands)}"))
            elif operation.operator == "where_present":
                if len(operation.arguments) != 1:
                    raise ValueError("where_present requires one argument")
                key = _key(operation)
                if key not in filter_keys:
                    filter_keys.add(key)
                    filters.append(Filter(operation.arguments[0]))

    return RelationPlan(
        scans,
        tuple(expands),
        tuple(filters) + tuple(Filter(item, "true") for item in predicates),
        tuple(compiled_outputs.items()),
    )


__all__ = ["expansion_scope", "lower_product"]
