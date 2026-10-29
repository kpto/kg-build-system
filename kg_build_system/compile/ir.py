"""Compilation IR: the frozen blueprint.

The blueprint contains only IR values. It holds no authoring Python classes, no
owner references and no derived identity; a consumer reads the facts it needs.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..binding.ir import BindingIR
from ..table.ir import ProjectionIR, SourceIR, StructIR, TableIR
from ..topology.ir import ComponentIR
from ..workflow.ir import BlueprintModuleIR


@dataclass(frozen=True, slots=True)
class BuildBlueprint:
    """The declarations and sources a compile reads."""

    structs: tuple[StructIR, ...]
    tables: tuple[TableIR, ...]
    components: tuple[ComponentIR, ...]
    projections: tuple[ProjectionIR, ...]
    bindings: tuple[BindingIR, ...]
    sources: tuple[SourceIR, ...] = ()
    modules: tuple[BlueprintModuleIR, ...] = ()


__all__ = ["BuildBlueprint"]
