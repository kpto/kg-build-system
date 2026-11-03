"""Load module compilers and compile a blueprint into a workflow contract.

The pipeline owns the order of module compilation and the rewrite of each
contribution's module reference to the class that was actually loaded. It reads a
blueprint; it never creates one.
"""
from __future__ import annotations

import asyncio
import importlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from kg_build_system.kernel.model.internal.json import FrozenObject, thaw_json
from ......kernel import CompilationContext
from .....contract.model.public import ContributionDTO, WorkflowContractDTO
from .adapter import wrap_contribution
from .assembly import assemble_contract
from .blueprint import GraphBlueprint, decompose


@dataclass(frozen=True, slots=True)
class _ModuleSpec:
    """A module class and its reconstructed configuration."""

    module_class: type[Any]
    configuration: Any


def _load_module(reference: Any) -> type[Any]:
    """Import and return the module class a module reference names."""
    module = importlib.import_module(reference.module_import)
    value: Any = module
    for part in reference.module_qualname.split("."):
        value = getattr(value, part)
    if not isinstance(value, type):
        raise TypeError(
            f"{reference.module_import}.{reference.module_qualname} is not a class"
        )
    return value


def _default_configuration(module_class: type[Any]) -> Any:
    return module_class.CONFIGURATION_TYPE()


def _configuration(module_class: type[Any], value: Any) -> Any:
    if value is None:
        return _default_configuration(module_class)
    if isinstance(value, FrozenObject):
        value = thaw_json(value)
    if isinstance(value, module_class.CONFIGURATION_TYPE):
        return value
    if isinstance(value, Mapping):
        return module_class.CONFIGURATION_TYPE(**value)
    return value


def _module_spec(value: Any) -> _ModuleSpec:
    module_class = getattr(value, "module_class", None)
    if isinstance(module_class, type):
        return _ModuleSpec(
            module_class,
            _configuration(module_class, getattr(value, "configuration", None)),
        )
    if isinstance(value, type):
        return _ModuleSpec(value, _default_configuration(value))
    import_module = getattr(value, "module_import", None)
    if isinstance(import_module, str):
        loaded = _load_module(value)
        return _ModuleSpec(
            loaded,
            _configuration(loaded, getattr(value, "configuration", None)),
        )
    raise TypeError(
        "modules must be registrations, module classes or module references"
    )


async def _compile_modules(
    blueprint: GraphBlueprint,
    modules: Sequence[Any],
    engine: Any,
) -> tuple[ContributionDTO, ...]:
    """Compile every supplied module against the blueprint's build."""
    build = decompose(blueprint)
    contributions: list[ContributionDTO] = []
    for value in modules:
        spec = _module_spec(value)
        context = CompilationContext(
            build=build,
            module_id=spec.module_class.ID,
            configuration=spec.configuration,
            blueprint=blueprint,
            engine=engine,
        )
        factory = getattr(spec.module_class, "compiler", None)
        if not callable(factory):
            raise TypeError(
                f"module {spec.module_class.__name__!r} has no compiler factory"
            )
        compiler: Any = factory(spec.configuration)
        contribution = wrap_contribution(await compiler.compile(context))
        definition = replace(
            contribution.module.reference,
            import_module=spec.module_class.__module__,
            class_qualname=spec.module_class.__qualname__,
            implementation_version=spec.module_class.VERSION,
        )
        contributions.append(replace(
            contribution,
            module=replace(contribution.module, reference=definition),
        ))
    return tuple(contributions)


def compile_blueprint(
    blueprint: GraphBlueprint, *, modules: Sequence[Any], engine: Any = None,
) -> WorkflowContractDTO:
    """Compile a blueprint and its module compilers into the contract DTO."""
    contributions = asyncio.run(_compile_modules(blueprint, modules, engine))
    return assemble_contract(contributions)


__all__ = ["compile_blueprint"]
