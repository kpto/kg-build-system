"""The asset language: logical source-data declarations.

An asset is a logical unit of source data. One asset may back many tables. Its
options describe the data's semantics, optional layout and governance; they do
not carry an adapter or code-generation request.

Example:
    ```python
    from kg_build_system import (
        Asset, AssetAuthority, AssetOptions, AssetSemantics,
    )

    class OpenTargets(Asset):
        options = AssetOptions(
            semantics=AssetSemantics(
                subject="gene-disease associations",
                coverage="all curated evidence",
                authority=AssetAuthority.PRIMARY,
                basis="Open Targets Platform release",
            ),
        )
    ```
"""
from __future__ import annotations

from .model.public import (
    Asset,
    AssetAuthority,
    AssetDescriptor,
    AssetGovernance,
    AssetLayout,
    AssetLicense,
    AssetOptions,
    AssetSemantics,
    asset_name,
    asset_reference,
)

__all__ = [
    "Asset",
    "AssetAuthority",
    "AssetDescriptor",
    "AssetGovernance",
    "AssetLayout",
    "AssetLicense",
    "AssetOptions",
    "AssetSemantics",
    "asset_name",
    "asset_reference",
]
