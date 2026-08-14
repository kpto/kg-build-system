"""Compose expression row semantics into an engine-neutral relational plan."""
from __future__ import annotations

import json
from collections.abc import Mapping

from ..expressions.dto import (
    ExpressionDTO as ExpressionNode,
    FieldReferenceExpressionDTO as FieldReferenceExpression,
    OperationExpressionDTO as OperationExpression,
    walk_expression_dto as walk_expression,
)
from ..expressions.dto_codec import encode_expression_dto as encode_expression
from ..expressions.ir import ExpressionNode as DomainExpressionNode
from ..expressions.mapping import expression_to_dto
from .dto import (
    ExpandDTO as Expand, FilterDTO as Filter, RelationPlanDTO as RelationPlan,
    ScanDTO as Scan,
)


def _key(expression: ExpressionNode) -> str:
    return json.dumps(
        encode_expression(expression), sort_keys=True, separators=(",", ":"),
    )


def _operators_post_order(expression: ExpressionNode):
    if not isinstance(expression, OperationExpression):
        return
    for argument in expression.arguments:
        yield from _operators_post_order(argument)
    yield expression


def lower_product(
    outputs: Mapping[str, ExpressionNode | DomainExpressionNode], relations: Mapping[str, str],
) -> RelationPlan:
    """Plan one projection or binding without leaking its row effects elsewhere."""
    if not outputs:
        raise ValueError("relational products require at least one output")
    compiled_outputs = {
        name: expression_to_dto(expression)
        if isinstance(expression, DomainExpressionNode)
        else expression
        for name, expression in outputs.items()
    }
    referenced = sorted({
        node.source
        for expression in compiled_outputs.values()
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
            if operation.operator == "each":
                effects = operation.row_semantics.effects
                if not effects or effects[-1].mode != "expand":
                    raise ValueError("each expressions require a local expansion effect")
                scope = effects[-1].scope
                if scope not in expansion_scopes:
                    expansion_scopes.add(scope)
                    expands.append(Expand(scope, operation.arguments[0], f"expanded{len(expands)}"))
            elif operation.operator == "when_present":
                if len(operation.arguments) != 1:
                    raise ValueError("when_present requires one argument")
                key = _key(operation)
                if key not in filter_keys:
                    filter_keys.add(key)
                    filters.append(Filter(operation.arguments[0]))

    return RelationPlan(scans, tuple(expands), tuple(filters), tuple(compiled_outputs.items()))


__all__ = ["lower_product"]
