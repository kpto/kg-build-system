"""Shared asset-table planning helpers.

A module planner that produces source-relation steps asks which tables the graph
reads and which asset each table comes from. The mechanism lives in the
package's private zone.
"""
from __future__ import annotations

from collections.abc import Mapping

from ...interpreter.model.public import GraphBlueprint
from ...model.public.asset_tables import AssetColumn, AssetTable


def asset_tables(blueprint: GraphBlueprint) -> tuple[AssetTable, ...]:
    """Return every asset-backed relation this graph reads.

    Only relations named by a binding expression, a binding row plan, a
    projection expression or a projection row plan are included. Tables are
    sorted by relation name and assigned ``kg_table_<n>``.

    Example:
        ```python
        from kg_build_system.distribution import create_blueprint
        from kg_build_system.distribution.service.public import asset_tables

        tables = asset_tables(create_blueprint(namespace_path="graph_pipeline"))
        ```
    """
    from .._private.asset_tables import asset_tables as implementation

    return implementation(blueprint)


def table_relations(blueprint: GraphBlueprint) -> Mapping[str, str]:
    """Map every table relation this graph reads to its plan relation name.

    Example:
        ```python
        from kg_build_system.distribution import create_blueprint
        from kg_build_system.distribution.service.public import table_relations

        relations = table_relations(create_blueprint(namespace_path="graph_pipeline"))
        ```
    """
    from .._private.asset_tables import table_relations as implementation

    return implementation(blueprint)


__all__ = ["AssetColumn", "AssetTable", "asset_tables", "table_relations"]
