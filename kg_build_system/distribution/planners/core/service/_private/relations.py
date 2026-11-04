"""Plan blueprint expressions and emit the engine's SQL."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kg_build_system.distribution.executors.duckdb.service.internal.emitters import (
    ArraySqlType,
    DuckDbInstructionEmitter,
    DuckDbSqlEmitter,
    NULL_GUARD_MACRO,
    SqlType,
    canonical_sql_type,
    row_source_sql as emit_row_source_sql,
)
from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.binding.model.internal.dto import (
    BindingDTO,
    EdgeBindingDTO,
)
from kg_build_system.distribution.languages.expressions.model.internal import (
    ExpressionDTO,
    FieldReferenceDTO,
)
from kg_build_system.distribution.languages.expressions.service.internal import (
    walk_expression_dto,
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
from kg_build_system.kernel.model.internal.types.dto import (
    ArrayTypeDTO,
    LogicalTypeDTO,
    NullableTypeDTO,
    UnitTypeDTO,
)
from .planning import plan_product


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


def expression_sources(expressions) -> set[str]:
    return {
        node.source
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
    return (
        expression_sources(
            column.expression for column in projection.columns
        )
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
    return expression_sources(binding_outputs(binding).values()) | _plan_sources(
        binding.rows,
    )


def _retarget(
    expression: ExpressionDTO, plan: RowSourcePlanDTO | None,
) -> ExpressionDTO:
    if plan is None:
        return expression
    source = plan_shape_source_name(plan)
    key = row_source_key(plan)
    if source == key:
        return expression
    return retarget_expression_dto(expression, {source: key})


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


_ROW_KEY = "_kg_named._kg_raw_build_key"
_RAW = "_kg_raw_"


def _claim_message(binding: BindingDTO, name: str) -> str:
    """A SQL expression naming the binding and, where possible, the row."""
    subject = f"{binding.component}.{name}"
    if name == "build_key":
        return _sql_string(
            f"{subject} is null, but it is declared non-null"
        )
    return (
        _sql_string(f"{subject} is null for build_key ")
        + " || coalesce(CAST(" + _ROW_KEY + " AS VARCHAR), '<null>')"
    )


def _sql_emitter(engine: DuckDbSqlEmitter | None) -> DuckDbSqlEmitter:
    return engine if engine is not None else DuckDbSqlEmitter()


def _instruction_emitter(
    engine: DuckDbSqlEmitter | None,
) -> DuckDbInstructionEmitter:
    emitter = _sql_emitter(engine).instruction_emitter
    return emitter if emitter is not None else DuckDbInstructionEmitter()


def row_source_sql(
    plan: RowSourcePlanDTO,
    relations: Mapping[str, str],
    shapes: Mapping[str, Any],
    *,
    engine: DuckDbSqlEmitter | None = None,
) -> str:
    """Render one row-source plan with the supplied SQL emitter."""
    return emit_row_source_sql(
        plan, relations, shapes, emitter=_instruction_emitter(engine),
    )


def _product_sql(
    outputs: Mapping[str, ExpressionDTO],
    relations: Mapping[str, str],
    *,
    engine: DuckDbSqlEmitter | None = None,
) -> str:
    instruction = _sql_emitter(engine).emit(plan_product(outputs, relations))
    payload = instruction.payload
    if not isinstance(payload, Mapping):
        raise ValueError("SQL emission requires an object payload")
    sql = payload.get("sql")
    if not isinstance(sql, str) or not sql:
        raise ValueError("SQL emission requires a SQL string")
    return sql


def projection_sql(
    graph: GraphBlueprint,
    relations: Mapping[str, str],
    projection: ProjectionDTO,
    *,
    engine: DuckDbSqlEmitter | None = None,
) -> str:
    del graph
    outputs = {
        column.name: _retarget(column.expression, projection.row_source)
        for column in projection.columns
        if column.expression is not None
    }
    return _product_sql(outputs, relations, engine=engine)


def binding_guard_projection(binding: BindingDTO) -> str:
    """The guarded select list reading a binding's renamed row values."""
    guarded: list[str] = []
    for name, expression in binding_outputs(binding).items():
        column = _quote_identifier(_RAW + name)
        if isinstance(expression.logical_type, NullableTypeDTO):
            guarded.append(f"{column} AS {_quote_identifier(name)}")
            continue
        guarded.append(
            f"{NULL_GUARD_MACRO}({column}, "
            f"{_claim_message(binding, name)}) AS {_quote_identifier(name)}"
        )
    return ", ".join(guarded)


def _binding_property_types(
    graph: GraphBlueprint, binding: BindingDTO,
) -> dict[str, LogicalTypeDTO]:
    """The declared types of the properties this binding fills."""
    component = next(
        (
            item for item in (*graph.graph.nodes, *graph.graph.edges)
            if item.name == binding.component
        ),
        None,
    )
    if component is None:
        return {}
    return {prop.name: prop.logical_type for prop in component.properties}


def binding_rename_projection(
    binding: BindingDTO,
    property_types: Mapping[str, LogicalTypeDTO] | None = None,
) -> str:
    """Cast each property to its declared type, then rename it for the guards."""
    declared = property_types or {}
    items: list[str] = []
    for name in binding_outputs(binding):
        column = _quote_identifier(name)
        raw = _quote_identifier(_RAW + name)
        logical_type = declared.get(name)
        sql_type = None if logical_type is None else sql_type_for(logical_type)
        if sql_type is None:
            items.append(f"{column} AS {raw}")
        else:
            items.append(
                f"CAST({column} AS {canonical_sql_type(sql_type)}) AS {raw}"
            )
    return ", ".join(items)


def binding_sql(
    graph: GraphBlueprint,
    relations: Mapping[str, str],
    binding: BindingDTO,
    *,
    engine: DuckDbSqlEmitter | None = None,
) -> str:
    """Emit one binding as the SQL of its graph records, guards included."""
    property_types = _binding_property_types(graph, binding)
    outputs = {
        name: _retarget(expression, binding.rows)
        for name, expression in binding_outputs(binding).items()
    }
    inner = _product_sql(outputs, relations, engine=engine)
    return (
        "WITH _kg_named AS ("
        f"SELECT {binding_rename_projection(binding, property_types)} "
        f"FROM ({inner}) AS _kg_rows"
        ") "
        f"SELECT {binding_guard_projection(binding)} FROM _kg_named"
    )


__all__ = [
    "NULL_GUARD_MACRO",
    "binding_outputs",
    "binding_guard_projection",
    "binding_rename_projection",
    "binding_sources",
    "binding_sql",
    "projection_sources",
    "projection_sql",
    "row_source_sql",
    "sql_type_for",
]
