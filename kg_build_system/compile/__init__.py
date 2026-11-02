"""Compilation: blueprint composition and the callable package.

The public composition functions, blueprint model and codec are re-exported from
:mod:`kg_build_system.compile.public`. The package also stays callable so
``from kg_build_system import compile`` keeps the composition-root behaviour.
"""
from __future__ import annotations

from types import ModuleType
from typing import Any

from .public import (
    BlueprintModule, BuildBlueprint, CompilableModule, CompilationContext,
    ModuleCompiler, compile, compile_build, compile_workflow,
    configure_blueprint_modules, create_blueprint, create_build,
    decode_blueprint, encode_blueprint, validate_blueprint,
)

__all__ = [
    "BlueprintModule", "BuildBlueprint", "CompilableModule",
    "CompilationContext", "ModuleCompiler", "compile", "compile_build",
    "compile_workflow", "configure_blueprint_modules", "create_blueprint",
    "create_build", "decode_blueprint", "encode_blueprint",
    "validate_blueprint",
]


class _CallableCompilePackage(ModuleType):
    """Keep ``from kg_build_system import compile`` callable."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        from ..api import compile as compile_build

        return compile_build(*args, **kwargs)


import sys as _sys

_sys.modules[__name__].__class__ = _CallableCompilePackage
