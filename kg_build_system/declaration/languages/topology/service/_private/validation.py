"""Invariant checks for the topology blueprint DTO."""
from __future__ import annotations


def validate_component(
    name: str,
    labels: tuple[str, ...],
    property_names: tuple[str, ...],
    parent: str | None,
    description: str | None,
) -> None:
    """Reject a topology component whose identity or members are incoherent."""
    if not name:
        raise ValueError("topology components require a non-empty name")
    if any(not label for label in labels):
        raise ValueError(f"component {name!r} labels must be non-empty")
    if len(labels) > 1:
        raise ValueError(f"component {name!r} carries at most one label")
    if len(property_names) != len(set(property_names)):
        raise ValueError(f"component {name!r} property names must be unique")
    if parent is not None and not parent:
        raise ValueError(f"component {name!r} parent must be a non-empty name")
    if description is not None and not description.strip():
        raise ValueError(f"component {name!r} description must be non-empty")


__all__ = ["validate_component"]
