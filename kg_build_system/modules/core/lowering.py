"""Plan and lower blueprint expressions into DuckDB SQL."""
from __future__ import annotations

from collections.abc import Mapping

from ...binding.ir import BindingIR as BindingDefinition, EdgeBindingIR as EdgeBindingDefinition
from ...compile.models import BuildBlueprint
from ...expressions.ir import (
    ExpressionIR,
    FieldReferenceExpressionIR as FieldReferenceExpression,
    walk_expression_ir,
)
from ...table.ir import ProjectionIR as ProjectionDefinition
from ...types.ir import (
    ArrayTypeIR, LogicalTypeIR, NullableTypeIR, UnitTypeIR,
)
from ...engines.duckdb import (
    NULL_GUARD_MACRO, ArraySqlType, SqlType, canonical_sql_type, lower_relation_sql,
)
from ...relational import lower_product


def sql_type_for(declared: LogicalTypeIR) -> SqlType | None:
    """The SQL shape one declared property type composes to, when it composes to one.

    The topology declaration is the contract. Nullability is dropped because an
    SQL type states no nullity, so ``Time | None`` is ``TIME`` and
    ``Array[Date] | None`` is ``DATE[]``. A custom scalar has no canonical SQL
    type, and a struct is not a graph property, so both pass through uncast.
    """
    if isinstance(declared, NullableTypeIR):
        return sql_type_for(declared.value)
    if isinstance(declared, UnitTypeIR):
        return declared.name
    if isinstance(declared, ArrayTypeIR):
        item = sql_type_for(declared.item)
        return None if item is None else ArraySqlType(item)
    return None


def expression_sources(expressions) -> set[str]:
    return {
        node.source
        for expression in expressions
        for node in walk_expression_ir(expression)
        if isinstance(node, FieldReferenceExpression)
    }


def projection_sources(projection: ProjectionDefinition) -> set[str]:
    return expression_sources(field.expression for field in projection.fields)


def binding_sources(binding: BindingDefinition) -> set[str]:
    expressions = [binding.build_key, *(value for _, value in binding.properties)]
    if isinstance(binding, EdgeBindingDefinition):
        expressions.extend((binding.source_build_key, binding.target_build_key))
    return expression_sources(expressions)


def binding_outputs(binding: BindingDefinition) -> dict[str, ExpressionIR]:
    """Every value one binding publishes — keys and properties in one dict."""
    outputs: dict[str, ExpressionIR] = {"build_key": binding.build_key}
    if isinstance(binding, EdgeBindingDefinition):
        outputs["source_build_key"] = binding.source_build_key
        outputs["target_build_key"] = binding.target_build_key
    outputs.update(dict(binding.properties))
    return outputs


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


_ROW_KEY = "_kg_named._kg_raw_build_key"
_RAW = "_kg_raw_"


def _claim_message(binding: BindingDefinition, name: str) -> str:
    """A SQL expression naming the declaration and, where possible, the row.

    A property or endpoint-key guard can name the row it belongs to, because the
    binding's row identity is its ``build_key`` output. ``build_key``'s own guard
    cannot — the key is the value in doubt — so it names the declaration alone.
    """
    subject = f"{binding.component}.{name}"
    if name == "build_key":
        return _sql_string(f"{subject} is null, but it is declared non-null")
    return (
        _sql_string(f"{subject} is null for build_key ")
        + " || coalesce(CAST(" + _ROW_KEY + " AS VARCHAR), '<null>')"
    )


def lower_projection_sql(
    graph: BuildBlueprint, relations: Mapping[str, str], projection: ProjectionDefinition,
) -> str:
    del graph
    outputs = {field.name: field.expression for field in projection.fields}
    return lower_relation_sql(lower_product(outputs, relations))


def lower_binding_guard_projection(binding: BindingDefinition) -> str:
    """The guarded select list reading a binding's renamed row values.

    Three levels, for two reasons. The guards must not alias their output to the
    same name as the column they read — DuckDB rejects a select item that
    shadows a source column of its own list — so a rename level hands each value
    under a private name first. And the guard level sits above the row product so
    a message can name the row it belongs to by ``build_key``.
    """
    guarded: list[str] = []
    for name, expression in binding_outputs(binding).items():
        column = _quote_identifier(_RAW + name)
        if isinstance(expression.logical_type, NullableTypeIR):
            guarded.append(f"{column} AS {_quote_identifier(name)}")
            continue
        guarded.append(
            f"{NULL_GUARD_MACRO}({column}, "
            f"{_claim_message(binding, name)}) AS {_quote_identifier(name)}"
        )
    return ", ".join(guarded)


def _binding_property_types(
    graph: BuildBlueprint, binding: BindingDefinition,
) -> dict[str, LogicalTypeIR]:
    """The declared types of the properties this binding fills."""
    component = next(
        (
            item for item in graph.components
            if item.name == binding.component and item.kind == binding.kind
        ),
        None,
    )
    if component is None:
        return {}
    return {prop.name: prop.logical_type for prop in component.properties}


def lower_binding_rename_projection(
    binding: BindingDefinition,
    property_types: Mapping[str, LogicalTypeIR] | None = None,
) -> str:
    """Cast each property to its declared type, then rename it for the guards.

    The cast is where topology becomes the physical schema: a nullable property
    whose every value is null would otherwise lower to an untyped `NULL` column
    and be materialized as an integer. Keys are not properties and pass through.
    """
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


def lower_binding_sql(
    graph: BuildBlueprint, relations: Mapping[str, str], binding: BindingDefinition,
) -> str:
    """Lower one binding to the SQL of its graph records, guards included.

    Every output whose static type is non-null carries a claim about the data, and
    the guard sits where that claim is delivered. Keys and properties share this
    one rule and one code path. An output already proven non-null by construction
    — after ``where_present`` or ``coalesce`` — simply never fires its guard.
    """
    property_types = _binding_property_types(graph, binding)
    inner = lower_relation_sql(lower_product(binding_outputs(binding), relations))
    return (
        "WITH _kg_named AS ("
        f"SELECT {lower_binding_rename_projection(binding, property_types)} "
        f"FROM ({inner}) AS _kg_rows"
        ") "
        f"SELECT {lower_binding_guard_projection(binding)} FROM _kg_named"
    )


__all__ = [
    "NULL_GUARD_MACRO",
    "binding_outputs",
    "binding_sources",
    "lower_binding_guard_projection",
    "lower_binding_rename_projection",
    "lower_binding_sql",
    "lower_projection_sql",
    "projection_sources",
]
