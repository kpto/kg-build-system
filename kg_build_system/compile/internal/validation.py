"""Cross-part validation of the blueprint aggregate."""
from __future__ import annotations

from .ir import BuildBlueprint


def validate_blueprint(blueprint: BuildBlueprint) -> None:
    """Reject a blueprint with no graph or with colliding symbols."""
    if not blueprint.components:
        raise ValueError("blueprints require at least one graph component")
    if not blueprint.bindings:
        raise ValueError("blueprints require at least one graph binding")
    symbols = (
        *(item.symbol_id for item in blueprint.structs),
        *(item.symbol_id for item in blueprint.tables),
        *(item.symbol_id for item in blueprint.components),
        *(item.symbol_id for item in blueprint.projections),
        *(item.symbol_id for item in blueprint.bindings),
        *(item.symbol_id for item in blueprint.sources),
    )
    if len(symbols) != len(set(symbols)):
        raise ValueError("blueprint symbol IDs must be unique")
    sources = tuple(item.table for item in blueprint.sources)
    if len(sources) != len(set(sources)):
        raise ValueError("source-bound table names must be unique")


__all__ = ["validate_blueprint"]
