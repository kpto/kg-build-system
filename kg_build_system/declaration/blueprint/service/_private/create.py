"""Create a graph blueprint from declarations.

The service collects and transcribes through the kernel registry, assembles the
layer DTOs and validates the result. It does not take modules and it does not
compile.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from .....kernel import Registry
from kg_build_system.declaration.languages.binding.service.internal import BindingLanguage
from kg_build_system.declaration.languages.table.service.internal import TableLanguage
from kg_build_system.declaration.languages.topology.service.internal import TopologyLanguage
from ...model.public import GraphBlueprint
from .assembly import assemble_blueprint
from .discovery import _ModuleNamespace, _Namespace, namespace_modules
from .validation import validate_blueprint


def _default_languages() -> tuple[Any, ...]:
    """Return the default table, topology and binding languages."""
    return (TableLanguage(), TopologyLanguage(), BindingLanguage())


def _part(build: Any, *names: str) -> Any:
    """Read the first language part present under one of ``names``."""
    for name in names:
        try:
            return build.part(name)
        except KeyError:
            continue
    raise KeyError(f"the build has none of the language parts {names!r}")


def create_blueprint(
    *,
    namespace_path: str | Path | None = None,
    bindings: Iterable[Any] = (),
    sources: Sequence[Any] = (),
    languages: Sequence[Any] | None = None,
) -> GraphBlueprint:
    """Collect declarations into a validated, frozen graph blueprint.

    Supply either ``namespace_path`` or explicit ``bindings`` and ``sources``.
    The declared languages are run through the kernel registry; each language
    collects and transcribes its own DTO, and this service assembles the DTOs
    into one blueprint.
    """
    explicit_bindings = tuple(bindings)
    explicit_sources = tuple(sources)
    if namespace_path is not None:
        if explicit_bindings or explicit_sources:
            raise ValueError(
                "namespace_path cannot be combined with bindings or sources"
            )
        namespace: Any = _ModuleNamespace(namespace_modules(namespace_path))
    else:
        namespace = _Namespace((*explicit_bindings, *explicit_sources))
    registry = Registry(tuple(languages or _default_languages()))
    build = registry.build(namespace)
    blueprint = assemble_blueprint(
        _part(build, "topology", "graph"),
        _part(build, "data", "table"),
        _part(build, "binding", "bindings"),
    )
    validate_blueprint(blueprint)
    return blueprint


__all__ = ["create_blueprint"]
