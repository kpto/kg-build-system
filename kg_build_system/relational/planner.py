"""Compose expression row effects into an engine-neutral relation plan."""
from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from ..expressions.interfaces import (
    ExpressionNode as DomainExpressionNode,
    encode_expression_ir as encode_expression,
    expression_to_ir,
    walk_expression_ir as walk_expression,
)
from ..expressions.ir import (
    ExpressionIR as ExpressionNode,
    FieldReferenceExpressionIR as FieldReferenceExpression,
    OperationExpressionIR as OperationExpression,
)
from .ir import (
    ExpandIR as Expand, FilterIR as Filter, RelationPlanIR as RelationPlan,
    ScanIR as Scan,
)

try:  # The operation registry is the preferred source of row-effect semantics.
    from ..expressions.interfaces import DEFAULT_OPERATIONS
except ImportError:  # pragma: no cover - compatibility with the older surface
    DEFAULT_OPERATIONS = None


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


def _spec_for(name: str) -> Any:
    """Look one operation up across the registry shapes the interface offers."""
    registry: Any = DEFAULT_OPERATIONS
    if registry is None:
        return None
    specs = getattr(registry, "specs", None)
    if isinstance(specs, Mapping):
        return specs.get(name)
    by_name = getattr(registry, "by_name", None)
    if isinstance(by_name, Mapping):
        return by_name.get(name)
    if isinstance(specs, (tuple, list)):
        for spec in specs:
            if getattr(spec, "name", None) == name:
                return spec
    get = getattr(registry, "get", None)
    if callable(get):
        try:
            return get(name)
        except (KeyError, ValueError):
            return None
    if isinstance(registry, Mapping):
        return registry.get(name)
    return None


def _predicate_index(operation: OperationExpression, spec: Any) -> int:
    """The argument that carries a filter's predicate.

    A row-effect spec names it explicitly where the interface can. The built-in
    value-scoped filter is the only operation with a non-leading predicate.
    """
    effect = getattr(spec, "row_effect", None)
    index = getattr(effect, "predicate_index", None)
    if isinstance(index, int):
        return index
    if operation.operator == "where_if":
        return 1
    return 0


def _row_effect(
    operation: OperationExpression,
) -> tuple[str, int | None] | None:
    """The planned row effect of one operation, or ``None`` when it preserves rows.

    The expression package owns the operation's meaning. The fallback names keep
    the older interface usable without making the planner test operator names in
    the normal path.
    """
    spec = _spec_for(operation.operator)
    if spec is not None:
        effect = getattr(spec, "row_effect", None)
        kind = getattr(effect, "kind", None)
        if kind is not None:
            value = getattr(kind, "value", kind)
            if value == "expand":
                return "expand", None
            if value == "filter":
                return "filter", getattr(effect, "predicate_index", None)
    # The built-in names fix the meaning the row-semantics value alone cannot:
    # ``where_present`` filters on its value, ``where_if`` on its second argument.
    if operation.operator == "expand":
        return "expand", None
    if operation.operator == "where_present":
        return "filter", None
    if operation.operator == "where_if":
        return "filter", 1
    if spec is not None:
        mode = getattr(effect, "mode", None)
        if mode == "expand":
            return "expand", None
        if mode == "filter":
            return "filter", _predicate_index(operation, spec)
    return None


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


__all__ = ["expansion_scope", "lower_product"]
