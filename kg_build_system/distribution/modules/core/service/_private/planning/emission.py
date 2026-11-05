"""Shared expression planning and SQL emission for the core planners.

The helpers here turn blueprint expressions into an engine-neutral relational
plan and then into SQL. They own the product rule, the retarget rule and the
canonical SQL type of a declared logical type.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from kg_build_system.distribution.languages.binding.model.internal.dto import (
    BindingDTO,
    EdgeBindingDTO,
)
from kg_build_system.distribution.languages.data.model.internal import (
    ProjectionDTO,
    RowSourcePlanDTO,
)
from kg_build_system.distribution.languages.data.service.internal import (
    plan_scan_sources,
    plan_shape_source_name,
    retarget_expression_dto,
    row_source_key,
)
from kg_build_system.distribution.languages.expressions.model.internal import (
    ExpressionDTO,
    FieldReferenceDTO,
    OperationExpressionDTO,
    RowSemantics,
)
from kg_build_system.distribution.languages.expressions.service.internal import (
    DEFAULT_OPERATIONS,
    RowEffectSpec,
    expression_to_document,
    walk_expression_dto,
)
from kg_build_system.distribution.service.internal.emission import (
    ArraySqlType,
    Expand,
    Filter,
    RelationPlan,
    RelationSqlEmitter,
    Scan,
    SqlEmitter,
    SqlType,
)
from kg_build_system.kernel.model.internal.types.dto import (
    ArrayTypeDTO,
    LogicalTypeDTO,
    NullableTypeDTO,
    UnitTypeDTO,
)


def sql_type_for(declared: LogicalTypeDTO) -> SqlType | None:
    """The SQL shape one declared property type composes to, when it has one."""
    if isinstance(declared, NullableTypeDTO):
        return sql_type_for(declared.value)
    if isinstance(declared, UnitTypeDTO):
        return declared.name
    if isinstance(declared, ArrayTypeDTO):
        item = sql_type_for(declared.item)
        return None if item is None else ArraySqlType(item)
    return None


def sql_emitter(engine: SqlEmitter) -> SqlEmitter:
    """The configured SQL emitter."""
    return engine


def instruction_emitter(engine: SqlEmitter) -> RelationSqlEmitter:
    """The instruction emitter behind a configured SQL emitter."""
    return sql_emitter(engine).instruction_emitter


def expression_sources(expressions: Any) -> set[str]:
    """Every relation named by a sequence of optional expressions."""
    return {
        node.field.relation
        for expression in expressions
        if expression is not None
        for node in walk_expression_dto(expression)
        if isinstance(node, FieldReferenceDTO)
    }


def _plan_sources(plan: RowSourcePlanDTO | None) -> set[str]:
    if plan is None:
        return set()
    return {*plan_scan_sources(plan), row_source_key(plan)}


def projection_sources(projection: ProjectionDTO) -> set[str]:
    """The declared inputs one projection reads."""
    return (
        expression_sources(column.expression for column in projection.columns)
        | _plan_sources(projection.row_source)
    )


def binding_outputs(binding: BindingDTO) -> dict[str, ExpressionDTO]:
    """Every value one binding publishes — keys and properties in one dict."""
    outputs: dict[str, ExpressionDTO] = {"build_key": binding.identity}
    if isinstance(binding, EdgeBindingDTO):
        outputs["source_build_key"] = binding.source_identity
        outputs["target_build_key"] = binding.target_identity
    outputs.update(dict(binding.properties))
    return outputs


def binding_sources(binding: BindingDTO) -> set[str]:
    """The declared inputs one binding reads."""
    return expression_sources(binding_outputs(binding).values()) | _plan_sources(
        binding.rows,
    )


def retarget_expression(
    expression: ExpressionDTO, plan: RowSourcePlanDTO | None,
) -> ExpressionDTO:
    """Point one expression at the plan's materialised relation name."""
    if plan is None:
        return expression
    source = plan_shape_source_name(plan)
    key = row_source_key(plan)
    if source == key:
        return expression
    return retarget_expression_dto(expression, {source: key})


def product_sql(
    outputs: Mapping[str, ExpressionDTO],
    relations: Mapping[str, str],
    *,
    engine: SqlEmitter,
) -> str:
    """Render one relational product through the configured SQL emitter."""
    instruction = sql_emitter(engine).emit(plan_product(outputs, relations))
    payload = instruction.payload
    if not isinstance(payload, Mapping):
        raise ValueError("SQL emission requires an object payload")
    sql = payload.get("sql")
    if not isinstance(sql, str) or not sql:
        raise ValueError("SQL emission requires a SQL string")
    return sql


def _key(expression: ExpressionDTO) -> str:
    return json.dumps(
        expression_to_document(expression),
        sort_keys=True,
        separators=(",", ":"),
    )


def expansion_scope(expression: OperationExpressionDTO) -> tuple[str, ...]:
    """Derive a stable, plan-local identity for one explicit ``expand`` operation."""
    if expression.operator.name != "expand":
        raise ValueError(
            "expansion scopes can only be derived for expand operations"
        )
    if len(expression.arguments) != 1:
        raise ValueError("expand requires one argument")
    argument = expression.arguments[0]
    if isinstance(argument, FieldReferenceDTO):
        return (argument.field.relation, argument.field.field, *argument.path)
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
    spec = DEFAULT_OPERATIONS.get(operation.operator.name)
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
    if operation.operator.name == "expand":
        return "expand", None
    if operation.operator.name == "drop_null":
        return "filter", None
    if operation.operator.name == "drop_if":
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
        node.field.relation
        for expression in (*compiled_outputs.values(), *predicates)
        for node in walk_expression_dto(expression)
        if isinstance(node, FieldReferenceDTO)
    })
    missing = set(referenced) - set(relations)
    if missing:
        raise ValueError(
            "no materialised relation for: " + ", ".join(sorted(missing))
        )
    if len(referenced) > 1:
        raise ValueError(
            "a relational product requires one driving source; additional "
            "sources must be introduced by an explicit lookup"
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
                    raise ValueError(
                        f"{operation.operator.name} requires one argument"
                    )
                scope = expansion_scope(operation)
                if scope not in expansion_scopes:
                    expansion_scopes.add(scope)
                    expands.append(Expand(
                        scope, operation.arguments[0],
                        f"expanded{len(expands)}",
                    ))
                continue
            if predicate_index is None:
                if len(operation.arguments) != 1:
                    raise ValueError(
                        f"{operation.operator.name} requires one argument"
                    )
                predicate = operation.arguments[0]
                mode = "present"
            else:
                if len(operation.arguments) <= predicate_index:
                    raise ValueError(
                        f"{operation.operator.name} requires a predicate"
                    )
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


__all__ = [
    "binding_outputs",
    "binding_sources",
    "expansion_scope",
    "expression_sources",
    "instruction_emitter",
    "plan_product",
    "product_sql",
    "projection_sources",
    "retarget_expression",
    "sql_emitter",
    "sql_type_for",
]
