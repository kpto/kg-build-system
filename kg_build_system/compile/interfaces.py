"""Compatibility shim for :mod:`kg_build_system.compile.internal`."""
from __future__ import annotations

from .internal import (
    BlueprintModule, BuildBlueprint, CompilableModule, CompilationContext,
    ModuleCompiler, decode_blueprint, encode_blueprint, validate_blueprint,
)

__all__ = [
    "BlueprintModule", "BuildBlueprint", "CompilableModule",
    "CompilationContext", "ModuleCompiler", "decode_blueprint",
    "encode_blueprint", "validate_blueprint",
]
