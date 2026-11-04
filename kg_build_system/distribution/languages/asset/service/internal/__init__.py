"""Framework-internal asset service interface.

Codec, source rendering and the kernel language adapter are resolved through
this package. The mechanisms live in ``service._private``; each name here is a
thin delegation.
"""
from __future__ import annotations

from .adapters import AssetLanguage
from .codec import assets_from_document, assets_to_document
from .source import render_asset_source

__all__ = [
    "AssetLanguage",
    "assets_from_document",
    "assets_to_document",
    "render_asset_source",
]
