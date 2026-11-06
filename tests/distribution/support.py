"""Shared declaration fixtures for blueprint tests."""

from __future__ import annotations

from kg_build_system import (
    Asset,
    AssetAuthority,
    AssetOptions,
    AssetProfile,
)


class TestEstate(Asset):
    """A logical asset for the blueprint fixtures."""

    options = AssetOptions(
        name="estate",
        profile=AssetProfile(
            subject="estate records",
            coverage="sites",
            authority=AssetAuthority.PRIMARY,
            basis="test fixture",
        ),
    )
