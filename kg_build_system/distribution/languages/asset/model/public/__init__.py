"""Author-facing model of the asset language."""
from __future__ import annotations

from .declarations import Asset
from .descriptor import AssetDescriptor, asset_name, asset_reference
from .options import (
    AssetAuthority,
    AssetGovernance,
    AssetLayout,
    AssetLicense,
    AssetOptions,
    AssetProfile,
)

__all__ = [
    "Asset",
    "AssetAuthority",
    "AssetDescriptor",
    "AssetGovernance",
    "AssetLayout",
    "AssetLicense",
    "AssetOptions",
    "AssetProfile",
    "asset_name",
    "asset_reference",
]
