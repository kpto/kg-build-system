"""Public composition API for knowledge-graph builds."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, overload

from .binding import Binding
from .compile.blueprint import BuildBlueprint
from .compile.compiler import (
    compile_blueprint as _compile_blueprint,
    create_blueprint as _create_blueprint,
)
from .compile.contracts import BuildContract, BuildSettings
from .modules.core import CoreModule
from .table import BoundSource
from .workflow.interfaces import ModuleRegistration


@overload
def create_blueprint(
    *,
    bindings: Iterable[Binding],
    sources: Sequence[BoundSource] = (),
    modules: Sequence[ModuleRegistration[Any]] = (),
) -> BuildBlueprint: ...


@overload
def create_blueprint(
    *,
    namespace_path: str | Path,
    bindings: Iterable[Binding] = (),
    sources: Sequence[BoundSource] = (),
    modules: Sequence[ModuleRegistration[Any]] = (),
) -> BuildBlueprint: ...


def create_blueprint(
    *,
    bindings: Iterable[Binding] = (),
    sources: Sequence[BoundSource] = (),
    modules: Sequence[ModuleRegistration[Any]] = (),
    namespace_path: str | Path | None = None,
) -> BuildBlueprint:
    """Create a blueprint with the mandatory core module as the final fallback."""
    composed_modules = (*modules, CoreModule())
    if namespace_path is None:
        return _create_blueprint(
            bindings=bindings,
            sources=sources,
            modules=composed_modules,
        )
    return _create_blueprint(
        namespace_path=namespace_path,
        bindings=bindings,
        sources=sources,
        modules=composed_modules,
    )


def compile_blueprint(
    *,
    blueprint: BuildBlueprint,
    sources: Sequence[BoundSource] = (),
    settings: BuildSettings | None = None,
) -> BuildContract:
    """Compile a composed blueprint into a frozen executable workflow."""
    return _compile_blueprint(
        blueprint=blueprint,
        sources=sources,
        settings=settings,
    )


__all__ = ["compile_blueprint", "create_blueprint"]
