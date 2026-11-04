"""Asset-table planning values returned to module planners.

These are frozen values, not services: a planner reads a relation, the asset it
comes from and the columns it declares.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from kg_build_system.kernel.model.public.types import LogicalType

if TYPE_CHECKING:
    from ...languages.asset.model.public import AssetDescriptor


@dataclass(frozen=True, slots=True)
class AssetColumn:
    """One declared column of an asset-backed relation.

    Example:
        ```python
        from kg_build_system.kernel.model.public.types import UnitType
        from kg_build_system.distribution.model.public import AssetColumn

        column = AssetColumn("site_id", UnitType("str"))
        assert column.name == "site_id"
        ```
    """

    name: str
    logical_type: LogicalType


@dataclass(frozen=True, slots=True)
class AssetTable:
    """One relation the graph reads, with the asset and columns it declares.

    Example:
        ```python
        from kg_build_system.distribution.model.public import AssetTable

        assert AssetTable.__name__ == "AssetTable"
        ```
    """

    asset: AssetDescriptor
    relation: str
    relation_name: str
    columns: tuple[AssetColumn, ...]


__all__ = ["AssetColumn", "AssetTable"]
