"""Framework-internal interface of the compilation domain.

Other subpackages implement the compile-time module protocol and read the
blueprint here. This subpackage has no author-facing surface: ``compile`` and
``create_blueprint`` are composed by :mod:`kg_build_system.api`. The compilation
IR is :mod:`kg_build_system.compile.ir`.
"""
from __future__ import annotations

from .codec import (
    blueprint_from_json,
    blueprint_json,
    decode_blueprint,
    encode_blueprint,
)
from .compiler import (
    compile_workflow,
    configure_blueprint_modules,
    create_blueprint,
)
from .ir import BuildBlueprint
from .protocols import (
    CompilableModule,
    CompilationContext,
    CompileModuleRegistration,
    ModuleCompiler,
)
from .validation import validate_blueprint

__all__ = [
    "BuildBlueprint",
    "CompilableModule",
    "CompilationContext",
    "CompileModuleRegistration",
    "ModuleCompiler",
    "blueprint_from_json",
    "blueprint_json",
    "compile_workflow",
    "configure_blueprint_modules",
    "create_blueprint",
    "decode_blueprint",
    "encode_blueprint",
    "validate_blueprint",
]
