"""Public composition API for knowledge-graph builds."""
from __future__ import annotations

import inspect
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, overload

from .binding import Binding
from .compile.compiler import (
    compile_workflow as _compile_workflow,
    configure_blueprint_modules as _configure_blueprint_modules,
    create_blueprint as _create_blueprint,
)
from .compile.models import BuildBlueprint
from .modules import ModuleRegistration, register_module
from .modules.core import CoreModule
from .table import BoundSource
from .workflow.ir import WorkflowContractIR


def _calling_namespace_path() -> Path:
    frame = inspect.currentframe()
    try:
        caller = (
            frame.f_back.f_back
            if frame is not None and frame.f_back is not None
            else None
        )
        if caller is None:
            raise RuntimeError("cannot determine the calling file")
        filename = caller.f_code.co_filename
        if filename.startswith("<"):
            raise RuntimeError(
                "the calling code does not have a filesystem namespace"
            )
        return Path(filename).resolve().parent
    finally:
        del frame


def _composed_modules(
    modules: Sequence[ModuleRegistration[Any]],
) -> tuple[ModuleRegistration[Any], ...]:
    return (*modules, register_module(CoreModule))


@overload
def create_blueprint(
    *, modules: Sequence[ModuleRegistration[Any]],
) -> BuildBlueprint: ...


@overload
def create_blueprint(
    *, namespace_path: str | Path, modules: Sequence[ModuleRegistration[Any]],
) -> BuildBlueprint: ...


@overload
def create_blueprint(
    *, bindings: Iterable[Binding], sources: Sequence[BoundSource],
    modules: Sequence[ModuleRegistration[Any]],
) -> BuildBlueprint: ...


def create_blueprint(
    *,
    modules: Sequence[ModuleRegistration[Any]],
    namespace_path: str | Path | None = None,
    bindings: Iterable[Binding] | None = None,
    sources: Sequence[BoundSource] | None = None,
) -> BuildBlueprint:
    """Create a blueprint from one namespace or explicit declarations."""
    composed_modules = _composed_modules(modules)
    if namespace_path is not None:
        if bindings is not None or sources is not None:
            raise ValueError(
                "namespace_path cannot be combined with bindings or sources"
            )
        return _create_blueprint(
            namespace_path=namespace_path,
            modules=composed_modules,
        )
    if bindings is not None or sources is not None:
        if bindings is None or sources is None:
            raise ValueError("bindings and sources must be supplied together")
        return _create_blueprint(
            bindings=bindings,
            sources=sources,
            modules=composed_modules,
        )
    return _create_blueprint(
        namespace_path=_calling_namespace_path(),
        modules=composed_modules,
    )


@overload
def compile(
    *, modules: Sequence[ModuleRegistration[Any]],
) -> WorkflowContractIR: ...


@overload
def compile(
    *, namespace_path: str | Path, modules: Sequence[ModuleRegistration[Any]],
) -> WorkflowContractIR: ...


@overload
def compile(
    *, bindings: Iterable[Binding], sources: Sequence[BoundSource],
    modules: Sequence[ModuleRegistration[Any]],
) -> WorkflowContractIR: ...


@overload
def compile(
    *, blueprint: BuildBlueprint, modules: Sequence[ModuleRegistration[Any]],
) -> WorkflowContractIR: ...


def compile(
    *,
    modules: Sequence[ModuleRegistration[Any]],
    namespace_path: str | Path | None = None,
    bindings: Iterable[Binding] | None = None,
    sources: Sequence[BoundSource] | None = None,
    blueprint: BuildBlueprint | None = None,
) -> WorkflowContractIR:
    """Compile one supported composition mode into an executable contract."""
    if blueprint is not None:
        if namespace_path is not None or bindings is not None or sources is not None:
            raise ValueError(
                "blueprint cannot be combined with namespace_path, bindings, or sources"
            )
        composed_blueprint = _configure_blueprint_modules(
            blueprint, _composed_modules(modules),
        )
    elif namespace_path is not None:
        if bindings is not None or sources is not None:
            raise ValueError(
                "namespace_path cannot be combined with bindings or sources"
            )
        composed_blueprint = _create_blueprint(
            namespace_path=namespace_path,
            modules=_composed_modules(modules),
        )
    elif bindings is not None or sources is not None:
        if bindings is None or sources is None:
            raise ValueError("bindings and sources must be supplied together")
        composed_blueprint = _create_blueprint(
            bindings=bindings,
            sources=sources,
            modules=_composed_modules(modules),
        )
    else:
        composed_blueprint = _create_blueprint(
            namespace_path=_calling_namespace_path(),
            modules=_composed_modules(modules),
        )
    return _compile_workflow(blueprint=composed_blueprint)


__all__ = ["compile", "create_blueprint"]
