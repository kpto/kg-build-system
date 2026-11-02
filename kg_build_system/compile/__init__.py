"""Compilation: pipeline and compatibility surface."""
from __future__ import annotations

from types import ModuleType
from typing import Any

from .interfaces import (
    BlueprintModule, BuildBlueprint, validate_blueprint,
)
from .pipeline import (
    compile_workflow, configure_blueprint_modules, create_blueprint,
)

__all__ = [
    "BlueprintModule", "BuildBlueprint", "compile_workflow",
    "configure_blueprint_modules", "create_blueprint", "validate_blueprint",
]


class _CallableCompilePackage(ModuleType):
    """Keep ``from kg_build_system import compile`` callable while the package
    ``kg_build_system.compile`` remains importable for its models and IR."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        from ..api import compile as compile_build

        return compile_build(*args, **kwargs)


import sys as _sys

_sys.modules[__name__].__class__ = _CallableCompilePackage
