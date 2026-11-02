"""Framework-internal interface of the compile package.

The blueprint aggregate, the compile-time module protocols, validation and the
canonical blueprint codec. The composition functions are exposed by the package
facade; their mechanisms are private.
"""
from __future__ import annotations

from ...kernel import CompilationContext
from .codec import decode_blueprint, encode_blueprint
from .ir import BlueprintModule, BuildBlueprint
from .protocols import CompilableModule, ModuleCompiler
from .validation import validate_blueprint

__all__ = [
    "BlueprintModule", "BuildBlueprint", "CompilableModule",
    "CompilationContext", "ModuleCompiler", "decode_blueprint",
    "encode_blueprint", "validate_blueprint",
]
