"""Framework-internal distribution service interface.

The shared rendering helpers and the asset-table planning query are thin
wrappers over :mod:`kg_build_system.distribution.service._private`.
"""
from __future__ import annotations

from .asset_tables import AssetColumn, AssetTable, asset_tables, table_relations

__all__ = ["AssetColumn", "AssetTable", "asset_tables", "table_relations"]
