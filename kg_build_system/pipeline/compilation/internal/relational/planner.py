"""Compose expression row effects into an engine-neutral relation plan."""
from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from .....declaration.foundations.expressions.internal import (
    DEFAULT_OPERATIONS,
    ExpressionDTO,
    FieldReferenceDTO,
    OperationExpressionDTO,
    RowEffectSpec,
    RowSemantics,
    expression_to_document,
    walk_expression_dto,
)
from .model import Expand, Filter, RelationPlan, Scan


def _key(expression: ExpressionDTO) -> str:
    return json.dumps(
        expression_to_document(expression),
        sort_keys=True,
        separators=(",", ":"),
    )


def expansion_scope(expression: OperationExpressionDTO) -> tuple[str, ...]:
    """Derive a stable, plan-local identity for one explicit ``expand`` operation."""
    if expression.operator != "expand":
        raise ValueError("expansion scopes can only be derived for expand operations")
    if len(expression.arguments) != 1:
        raise ValueError("expand requires one argument")
    argument = expression.arguments[0]
    if isinstance(argument, FieldReferenceDTO):
        return (argument.source, *argument.path)
    if (
        isinstance(argument, OperationExpressionDTO)
        and argument.operator == "struct_field"
        and len(argument.arguments) == 1
        and isinstance(argument.arguments[0], OperationExpressionDTO)
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


def _operators_post_order(expression: ExpressionDTO):
    if not isinstance(expression, OperationExpressionDTO):
        return
    for argument in expression.arguments:
        yield from _operators_post_order(argument)
    yield expression


def _row_effect(
    operation: OperationExpressionDTO,
) -> tuple[str, int | None] | None:
    """The planned row effect of one operation, or ``None`` when rows are kept."""
    spec = DEFAULT_OPERATIONS.get(operation.operator)
    if spec is not None:
        effect: Any = spec.row_effect
        if isinstance(effect, RowEffectSpec):
            if effect.kind == "expand":
                return "expand", None
            return "filter", effect.predicate_index
        if isinstance(effect, RowSemantics):
            if effect.mode == "expand":
                return "expand", None
            if effect.mode == "filter":
                return "filter", None
    if operation.operator == "expand":
        return "expand", None
    if operation.operator == "where_present":
        return "filter", None
    if operation.operator == "where_if":
        return "filter", 1
    return None


def plan_product(
    outputs: Mapping[str, ExpressionDTO],
    relations: Mapping[str, str],
    *,
    predicates: tuple[ExpressionDTO, ...] = (),
) -> RelationPlan:
    """Plan one projection or binding without leaking its row effects elsewhere."""
    if not outputs:
        raise ValueError("relational products require at least one output")
    compiled_outputs = dict(outputs)
    referenced = sorted({
        node.source
        for expression in (*compiled_outputs.values(), *predicates)
        for node in walk_expression_dto(expression)
        if isinstance(node, FieldReferenceDTO)
    })
    missing = set(referenced) - set(relations)
    if missing:
        raise ValueError("no materialised relation for: " + ", ".join(sorted(missing)))
    if len(referenced) > 1:
        raise ValueError(
            "a relational product requires one driving source; additional sources "
            "must be introduced by an explicit lookup"
        )
    scans = tuple(
        Scan(source, relations[source], f"t{index}")
        for index, source in enumerate(referenced)
    )

    expands: list[Expand] = []
    filters: list[Filter] = []
    expansion_scopes: set[tuple[str, ...]] = set()
    filter_keys: set[str] = set()
    for expression in (*compiled_outputs.values(), *predicates):
        for operation in _operators_post_order(expression):
            effect = _row_effect(operation)
            if effect is None:
                continue
            kind, predicate_index = effect
            if kind == "expand":
                if len(operation.arguments) != 1:
                    raise ValueError(f"{operation.operator} requires one argument")
                scope = expansion_scope(operation)
                if scope not in expansion_scopes:
                    expansion_scopes.add(scope)
                    expands.append(Expand(
                        scope, operation.arguments[0], f"expanded{len(expands)}",
                    ))
                continue
            if predicate_index is None:
                if len(operation.arguments) != 1:
                    raise ValueError(f"{operation.operator} requires one argument")
                predicate = operation.arguments[0]
                mode = "present"
            else:
                if len(operation.arguments) <= predicate_index:
                    raise ValueError(f"{operation.operator} requires a predicate")
                predicate = operation.arguments[predicate_index]
                mode = "true"
            key = _key(operation)
            if key not in filter_keys:
                filter_keys.add(key)
                filters.append(Filter(predicate, mode))

    return RelationPlan(
        scans,
        tuple(expands),
        tuple(filters) + tuple(Filter(item, "true") for item in predicates),
        tuple(compiled_outputs.items()),
    )


__all__ = ["expansion_scope", "plan_product"]
