"""Plan and lower blueprint expressions into DuckDB SQL."""
from __future__ import annotations

from collections.abc import Mapping

from ...binding.ir import BindingIR as BindingDefinition, EdgeBindingIR as EdgeBindingDefinition
from ...compile.models import BuildBlueprint
from ...table.ir import ProjectionIR as ProjectionDefinition
from ...engines.duckdb import lower_relation_sql
from ...expressions.ir import (
    FieldReferenceExpressionIR as FieldReferenceExpression,
    walk_expression_ir as walk_expression,
)
from ...relational import lower_product


def expression_sources(expressions) -> set[str]:
    return {
        node.source
        for expression in expressions
        for node in walk_expression(expression)
        if isinstance(node, FieldReferenceExpression)
    }


def projection_sources(projection: ProjectionDefinition) -> set[str]:
    return expression_sources(field.expression for field in projection.fields)


def binding_sources(binding: BindingDefinition) -> set[str]:
    expressions = [binding.build_key, *(value for _, value in binding.properties)]
    if isinstance(binding, EdgeBindingDefinition):
        expressions.extend((binding.source_build_key, binding.target_build_key))
    return expression_sources(expressions)


def lower_projection_sql(
    graph: BuildBlueprint, relations: Mapping[str, str], projection: ProjectionDefinition,
) -> str:
    del graph
    outputs = {field.name: field.expression for field in projection.fields}
    return lower_relation_sql(lower_product(outputs, relations))


def lower_binding_sql(
    graph: BuildBlueprint, relations: Mapping[str, str], binding: BindingDefinition,
) -> str:
    del graph
    outputs = {"build_key": binding.build_key}
    if isinstance(binding, EdgeBindingDefinition):
        outputs.update({
            "source_build_key": binding.source_build_key,
            "target_build_key": binding.target_build_key,
        })
    outputs.update(binding.properties)
    return lower_relation_sql(lower_product(outputs, relations))


__all__ = [
    "binding_sources", "expression_sources", "lower_binding_sql",
    "lower_projection_sql", "projection_sources",
]
