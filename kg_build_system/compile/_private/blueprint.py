"""Private blueprint lowering and module registration."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from ...binding.internal import BindingLanguage
from ...kernel import Registry
from ...table.internal import TableLanguage
from ...topology.internal import TopologyLanguage
from ..internal import (
    BlueprintModule, BuildBlueprint, validate_blueprint,
)
from .discovery import _ModuleNamespace, _Namespace, namespace_modules


def default_languages() -> tuple[Any, ...]:
    """Return the default table, topology and binding languages."""
    return (TableLanguage(), TopologyLanguage(), BindingLanguage())


def _configuration(value: Any) -> Any:
    """Internal helper for configuration."""
    to_json = getattr(value, "to_json", None)
    return to_json() if callable(to_json) else value


def _modules_from_registrations(
    registrations: Sequence[Any],
) -> tuple[BlueprintModule, ...]:
    """Freeze module registrations into blueprint module references."""
    result = []
    for registration in registrations:
        cls = registration.module_class
        result.append(BlueprintModule(
            cls.ID, cls.__module__, cls.__qualname__,
            _configuration(registration.configuration),
        ))
    return tuple(result)


def create_blueprint(
    *,
    bindings: Iterable[Any] = (),
    sources: Sequence[Any] = (),
    modules: Sequence[Any] = (),
    namespace_path: str | Path | None = None,
    languages: Sequence[Any] | None = None,
) -> BuildBlueprint:
    """Lower declarations and module registrations into a validated blueprint."""
    if namespace_path is not None:
        namespace = _ModuleNamespace(namespace_modules(namespace_path))
    else:
        namespace = _Namespace((*tuple(bindings), *tuple(sources)))
    registry = Registry(languages or default_languages())
    build = registry.build(namespace)
    data = build.part("data")
    topology = build.part("topology")
    binding = build.part("binding")
    blueprint = BuildBlueprint(
        data.structs, data.tables, topology, data.projections, binding,
        data.sources, _modules_from_registrations(modules),
    )
    validate_blueprint(blueprint)
    return blueprint


def configure_blueprint_modules(
    blueprint: BuildBlueprint, modules: Sequence[Any],
) -> BuildBlueprint:
    """Return a blueprint with its module composition replaced."""
    return replace(
        blueprint, modules=_modules_from_registrations(modules),
    )


__all__ = [
    "configure_blueprint_modules", "create_blueprint", "default_languages",
]
