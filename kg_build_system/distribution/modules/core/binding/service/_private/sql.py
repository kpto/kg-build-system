"""Emit one binding as the SQL of its graph records."""
from __future__ import annotations

from collections.abc import Mapping

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.binding.model.internal.dto import (
    BindingDTO,
)
from kg_build_system.distribution.modules.core.service._private.planning.emission import (
    binding_outputs,
    product_sql,
    retarget_expression,
)
from kg_build_system.distribution.modules.duckdb.service.internal.emitters import (
    DuckDbSqlEmitter,
)
from kg_build_system.kernel.model.internal.types.dto import LogicalTypeDTO
from .guards import binding_guard_projection, binding_rename_projection


def binding_property_types(
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


def binding_sql(
    graph: GraphBlueprint,
    relations: Mapping[str, str],
    binding: BindingDTO,
    *,
    engine: DuckDbSqlEmitter | None = None,
) -> str:
    """Emit one binding as the SQL of its graph records, guards included."""
    property_types = binding_property_types(graph, binding)
    outputs = {
        name: retarget_expression(expression, binding.rows)
        for name, expression in binding_outputs(binding).items()
    }
    inner = product_sql(outputs, relations, engine=engine)
    return (
        "WITH _kg_named AS ("
        f"SELECT {binding_rename_projection(binding, property_types)} "
        f"FROM ({inner}) AS _kg_rows"
        ") "
        f"SELECT {binding_guard_projection(binding)} FROM _kg_named"
    )


__all__ = ["binding_property_types", "binding_sql"]
