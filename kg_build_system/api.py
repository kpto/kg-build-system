"""Composition root for knowledge-graph builds.

The canonical flow hides the blueprint handle:

```python
contract = compile(modules=modules)
```

An advanced caller can create and inspect the blueprint explicitly:

```python
blueprint = create_blueprint(namespace_path=ROOT)
contract = compile_blueprint(blueprint, modules=modules)
```
"""
from __future__ import annotations

import inspect
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from .declaration.blueprint import GraphBlueprint, create_blueprint as _create_blueprint
from .declaration.languages.binding import Binding
from .declaration.languages.table import BoundSource
from .pipeline.compile import compile_blueprint
from .pipeline.execution import execute


def _calling_namespace_path() -> Path:
    package_root = Path(__file__).resolve().parent
    frame = inspect.currentframe()
    try:
        frame = frame.f_back if frame is not None else None
        while frame is not None:
            filename = frame.f_code.co_filename
            if not filename.startswith("<"):
                path = Path(filename).resolve()
                if not path.is_relative_to(package_root):
                    return path.parent
            frame = frame.f_back
        raise RuntimeError("cannot determine the calling file")
    finally:
        del frame


def _with_core(modules: Sequence[Any]) -> tuple[Any, ...]:
    from .distribution import CoreModule, register_module

    ids = {getattr(item.module_class, "ID", None) for item in modules}
    if CoreModule.ID in ids:
        return tuple(modules)
    return (*modules, register_module(CoreModule))


def create_blueprint(
    *,
    namespace_path: str | Path | None = None,
    bindings: Iterable[Binding] = (),
    sources: Sequence[BoundSource] = (),
    languages: Sequence[Any] | None = None,
) -> GraphBlueprint:
    """Create the semantic blueprint for one declaration namespace.

    Example:
        ```python
        from pathlib import Path
        from kg_build_system import create_blueprint

        blueprint = create_blueprint(namespace_path=Path("my_project"))
        ```
    """
    binding_values = tuple(bindings)
    if binding_values or sources:
        if namespace_path is not None:
            raise ValueError(
                "namespace_path cannot be combined with bindings or sources"
            )
        return _create_blueprint(
            bindings=binding_values, sources=sources, languages=languages,
        )
    if namespace_path is None:
        namespace_path = _calling_namespace_path()
    return _create_blueprint(namespace_path=namespace_path, languages=languages)


def compile(
    *,
    modules: Sequence[Any] = (),
    namespace_path: str | Path | None = None,
    bindings: Iterable[Binding] | None = None,
    sources: Sequence[BoundSource] | None = None,
    blueprint: GraphBlueprint | None = None,
    engine: Any = None,
) -> Any:
    """Compile a blueprint into a workflow contract.

    This is the canonical shortcut: it creates the blueprint when one is not
    supplied and then compiles it. `compile_blueprint` is the explicit form.

    Example:
        ```python
        from kg_build_system import compile
        from kg_build_system.distribution import (
            FileModule, FileModuleConfiguration, register_module,
        )

        contract = compile(
            modules=(
                register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
            ),
        )
        ```
    """
    if blueprint is not None:
        if namespace_path is not None or bindings is not None or sources is not None:
            raise ValueError(
                "blueprint cannot be combined with namespace_path, bindings, or sources"
            )
        prepared = blueprint
    else:
        prepared = create_blueprint(
            namespace_path=namespace_path,
            bindings=() if bindings is None else bindings,
            sources=() if sources is None else sources,
        )
    return compile_blueprint(prepared, modules=_with_core(modules), engine=engine)


__all__ = [
    "GraphBlueprint", "compile", "compile_blueprint", "create_blueprint",
    "execute",
]
