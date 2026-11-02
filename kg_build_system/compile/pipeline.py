"""Compilation pipeline over the kernel and the default languages."""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
from collections.abc import Iterable, Sequence
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import Any

from ..binding.interfaces import BindingLanguage
from ..kernel import BuildIR, CompilationContext, Registry
from ..table.interfaces import TableLanguage
from ..topology.interfaces import TopologyLanguage
from .interfaces import (
    BuildBlueprint, BlueprintModule, CompilableModule, validate_blueprint,
)


class _Namespace:
    def __init__(self, values: Sequence[object]) -> None:
        self._values = tuple(values)

    def values(self) -> Sequence[object]:
        return self._values


class _ModuleNamespace:
    def __init__(self, modules: Sequence[ModuleType]) -> None:
        self._modules = tuple(modules)

    def values(self) -> Sequence[object]:
        result: list[object] = []
        for module in self._modules:
            result.extend(
                value for name, value in vars(module).items()
                if not name.startswith("_")
            )
        return tuple(result)


def default_languages() -> tuple[Any, ...]:
    return (TableLanguage(), TopologyLanguage(), BindingLanguage())


def _namespace_modules(path: str | Path) -> tuple[ModuleType, ...]:
    root = Path(path).resolve()
    parent = root.parent
    package = root.name
    names: set[str] = {package}
    for directory, children, files in os.walk(root):
        current = Path(directory)
        children[:] = [
            child for child in children
            if child.isidentifier()
            and child not in {"build", "node_modules", "__pycache__"}
        ]
        relative = current.relative_to(root)
        parts = (package, *relative.parts) if relative.parts else (package,)
        if current != root:
            names.add(".".join(parts))
        for file in files:
            if not file.endswith(".py") or file == "__init__.py":
                continue
            stem = file[:-3]
            if stem.isidentifier():
                names.add(".".join((*parts, stem)))
    sys.path.insert(0, str(parent))
    try:
        return tuple(importlib.import_module(name) for name in sorted(names))
    finally:
        sys.path.remove(str(parent))


def _configuration(value: Any) -> Any:
    to_json = getattr(value, "to_json", None)
    return to_json() if callable(to_json) else value


def _modules_from_registrations(registrations: Sequence[Any]) -> tuple[BlueprintModule, ...]:
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
    if namespace_path is not None:
        namespace = _ModuleNamespace(_namespace_modules(namespace_path))
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
    return replace(blueprint, modules=_modules_from_registrations(modules))


def _load_module(reference: BlueprintModule) -> type[CompilableModule]:
    module = importlib.import_module(reference.module_import)
    value: Any = module
    for part in reference.module_qualname.split("."):
        value = getattr(value, part)
    if not isinstance(value, type):
        raise TypeError(f"{reference.module_import}.{reference.module_qualname} is not a class")
    return value


async def _compile_modules(
    blueprint: BuildBlueprint, build: BuildIR, engine: Any,
) -> tuple[Any, ...]:
    contributions = []
    for reference in blueprint.modules:
        cls = _load_module(reference)
        configuration = cls.CONFIGURATION_TYPE(**(reference.configuration or {}))
        context = CompilationContext(
            build=build, module_id=cls.ID, configuration=configuration,
            blueprint=blueprint, engine=engine,
        )
        compiler = await cls.create_compiler(context)
        contribution = await compiler.compile(context)
        definition = replace(
            contribution.module.reference,
            import_module=cls.__module__,
            class_qualname=cls.__qualname__,
            implementation_version=cls.VERSION,
        )
        contributions.append(replace(
            contribution,
            module=replace(contribution.module, reference=definition),
        ))
    return tuple(contributions)


def compile_workflow(
    *, blueprint: BuildBlueprint, engine: Any = None,
) -> Any:
    from ..workflow.interfaces import assemble_workflow, create_workflow_contract

    build = BuildIR({
        "data": type("_Data", (), {
            "structs": blueprint.structs, "tables": blueprint.tables,
            "projections": blueprint.projections, "sources": blueprint.sources,
        })(),
        "topology": blueprint.components,
        "binding": blueprint.bindings,
    })
    contributions = asyncio.run(_compile_modules(blueprint, build, engine))
    workflow = assemble_workflow(contributions)
    provenance = {
        "compile": {
            "blueprint_fingerprint": _fingerprint(blueprint),
        },
    }
    from typing import cast
    from pydantic import JsonValue

    return create_workflow_contract(
        workflow, provenance=cast(JsonValue, provenance),
    )


def _fingerprint(blueprint: BuildBlueprint) -> str:
    from hashlib import sha256
    import json

    from .interfaces import encode_blueprint

    payload = json.dumps(
        encode_blueprint(blueprint), sort_keys=True, separators=(",", ":"),
        default=str,
    ).encode()
    return sha256(payload).hexdigest()


__all__ = [
    "compile_workflow", "configure_blueprint_modules", "create_blueprint",
    "default_languages",
]
