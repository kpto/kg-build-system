"""Internal asset-table planning interface."""
from __future__ import annotations

from collections.abc import Mapping

from ...interpreter.model.public import GraphBlueprint
from ...model.public.asset_tables import AssetColumn, AssetTable


def asset_tables(blueprint: GraphBlueprint) -> tuple[AssetTable, ...]:
    """Return every asset-backed relation this graph reads."""
    from .._private.asset_tables import asset_tables as implementation

    return implementation(blueprint)


def table_relations(blueprint: GraphBlueprint) -> Mapping[str, str]:
    """Map every table relation this graph reads to its plan relation name."""
    from .._private.asset_tables import table_relations as implementation

    return implementation(blueprint)


__all__ = ["AssetColumn", "AssetTable", "asset_tables", "table_relations"]
