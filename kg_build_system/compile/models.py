"""Compilation-domain models and the aggregate declaration blueprint."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from ..binding.ir import BindingIR
from ..table.ir import ProjectionIR, SourceIR, StructIR, TableIR
from ..topology.ir import ComponentIR
from ..workflow.ir import BlueprintModuleIR


BLUEPRINT_SCHEMA_VERSION: Final = 2


@dataclass(frozen=True, slots=True)
class CompilationSettings:
    """Settings that affect compilation rather than workflow execution."""


@dataclass(frozen=True, slots=True)
class SourceOverride:
    table: str
    original: SourceIR | None
    override: SourceIR


@dataclass(frozen=True, slots=True)
class CompilationOverrides:
    sources: tuple[SourceOverride, ...] = ()


@dataclass(frozen=True, slots=True)
class BuildBlueprint:
    """A compilation artifact containing no authoring Python classes."""

    structs: tuple[StructIR, ...]
    tables: tuple[TableIR, ...]
    components: tuple[ComponentIR, ...]
    projections: tuple[ProjectionIR, ...]
    bindings: tuple[BindingIR, ...]
    sources: tuple[SourceIR, ...] = ()
    modules: tuple[BlueprintModuleIR, ...] = ()
    schema_version: Literal[2] = 2


__all__ = [
    "BLUEPRINT_SCHEMA_VERSION", "BuildBlueprint", "CompilationOverrides",
    "CompilationSettings", "SourceOverride",
]
