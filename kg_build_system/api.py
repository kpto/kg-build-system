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


@overload
def compile(
    *,
    blueprint: BuildBlueprint,
    source_overrides: Sequence[BoundSource] = (),
    settings: BuildSettings | None = None,
) -> BuildContract: ...


@overload
def compile(
    *,
    bindings: Iterable[Binding],
    sources: Sequence[BoundSource] = (),
    source_overrides: Sequence[BoundSource] = (),
    modules: Sequence[ModuleRegistration[Any]] = (),
    settings: BuildSettings | None = None,
) -> BuildContract: ...


@overload
def compile(
    *,
    namespace_path: str | Path,
    bindings: Iterable[Binding] = (),
    sources: Sequence[BoundSource] = (),
    source_overrides: Sequence[BoundSource] = (),
    modules: Sequence[ModuleRegistration[Any]] = (),
    settings: BuildSettings | None = None,
) -> BuildContract: ...


def compile(
    *,
    blueprint: BuildBlueprint | None = None,
    bindings: Iterable[Binding] = (),
    sources: Sequence[BoundSource] = (),
    source_overrides: Sequence[BoundSource] = (),
    modules: Sequence[ModuleRegistration[Any]] = (),
    namespace_path: str | Path | None = None,
    settings: BuildSettings | None = None,
) -> BuildContract:
    """Compile authoring declarations directly into an executable contract."""
    authoring_bindings = tuple(bindings)
    if blueprint is not None:
        if authoring_bindings or sources or modules or namespace_path is not None:
            raise ValueError(
                "blueprint cannot be combined with authoring declarations, "
                "sources, modules, or namespace_path"
            )
        composed_blueprint = blueprint
    else:
        if namespace_path is None:
            composed_blueprint = create_blueprint(
                bindings=authoring_bindings,
                sources=sources,
                modules=modules,
            )
        else:
            composed_blueprint = create_blueprint(
                namespace_path=namespace_path,
                bindings=authoring_bindings,
                sources=sources,
                modules=modules,
            )
    return _compile_blueprint(
        blueprint=composed_blueprint,
        sources=source_overrides,
        settings=settings,
    )


__all__ = ["compile", "create_blueprint"]
