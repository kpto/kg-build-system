"""Composition root for knowledge-graph builds."""
from __future__ import annotations

import inspect
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, overload

from .compile import BuildBlueprint, compile_workflow, configure_blueprint_modules, create_blueprint as _create_blueprint
from .table import BoundSource
from .binding import Binding


def _calling_namespace_path() -> Path:
    frame = inspect.currentframe()
    try:
        caller = frame.f_back.f_back if frame is not None and frame.f_back is not None else None
        if caller is None:
            raise RuntimeError("cannot determine the calling file")
        filename = caller.f_code.co_filename
        if filename.startswith("<"):
            raise RuntimeError("the calling code does not have a filesystem namespace")
        return Path(filename).resolve().parent
    finally:
        del frame


def _composed_modules(modules: Sequence[Any]) -> tuple[Any, ...]:
    from .modules import register_module
    from .modules.core import CoreModule

    return (*modules, register_module(CoreModule))


def create_blueprint(
    *,
    modules: Sequence[Any],
    namespace_path: str | Path | None = None,
    bindings: Iterable[Binding] | None = None,
    sources: Sequence[BoundSource] | None = None,
) -> BuildBlueprint:
    composed = _composed_modules(modules)
    if namespace_path is not None:
        if bindings is not None or sources is not None:
            raise ValueError("namespace_path cannot be combined with bindings or sources")
        return _create_blueprint(namespace_path=namespace_path, modules=composed)
    if bindings is not None or sources is not None:
        if bindings is None or sources is None:
            raise ValueError("bindings and sources must be supplied together")
        return _create_blueprint(bindings=bindings, sources=sources, modules=composed)
    return _create_blueprint(namespace_path=_calling_namespace_path(), modules=composed)


def compile(
    *,
    modules: Sequence[Any],
    namespace_path: str | Path | None = None,
    bindings: Iterable[Binding] | None = None,
    sources: Sequence[BoundSource] | None = None,
    blueprint: BuildBlueprint | None = None,
    engine: Any = None,
) -> Any:
    composed = _composed_modules(modules)
    if blueprint is not None:
        if namespace_path is not None or bindings is not None or sources is not None:
            raise ValueError("blueprint cannot be combined with namespace_path, bindings, or sources")
        configured = configure_blueprint_modules(blueprint, composed)
    elif namespace_path is not None:
        if bindings is not None or sources is not None:
            raise ValueError("namespace_path cannot be combined with bindings or sources")
        configured = _create_blueprint(namespace_path=namespace_path, modules=composed)
    elif bindings is not None or sources is not None:
        if bindings is None or sources is None:
            raise ValueError("bindings and sources must be supplied together")
        configured = _create_blueprint(bindings=bindings, sources=sources, modules=composed)
    else:
        configured = _create_blueprint(namespace_path=_calling_namespace_path(), modules=composed)
    return compile_workflow(blueprint=configured, engine=engine)


__all__ = ["compile", "create_blueprint"]
