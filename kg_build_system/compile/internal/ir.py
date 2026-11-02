"""Compilation IR: the blueprint aggregate."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class BlueprintModule:
    """A module registration frozen into the blueprint."""

    module_id: str
    module_import: str
    module_qualname: str
    configuration: Any = None


@dataclass(frozen=True, slots=True)
class BuildBlueprint:
    """The frozen aggregate of declarations and module registrations."""

    structs: tuple[Any, ...]
    tables: tuple[Any, ...]
    components: tuple[Any, ...]
    projections: tuple[Any, ...]
    bindings: tuple[Any, ...]
    sources: tuple[Any, ...] = ()
    modules: tuple[BlueprintModule, ...] = ()


__all__ = ["BlueprintModule", "BuildBlueprint"]
