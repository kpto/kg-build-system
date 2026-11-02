"""Private compilation pipeline over the kernel and the workflow assembler."""
from __future__ import annotations

import asyncio
import importlib
from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from ...kernel import BuildIR, CompilationContext
from ..internal import (
    BlueprintModule, BuildBlueprint, CompilableModule,
)
from .blueprint import _modules_from_registrations


def _load_module(reference: BlueprintModule) -> type[CompilableModule]:
    """Import and return the module class a blueprint reference names."""
    module = importlib.import_module(reference.module_import)
    value: Any = module
    for part in reference.module_qualname.split("."):
        value = getattr(value, part)
    if not isinstance(value, type):
        raise TypeError(
            f"{reference.module_import}.{reference.module_qualname} is not a class"
        )
    return value


async def _compile_modules(
    blueprint: BuildBlueprint | None, build: BuildIR, engine: Any,
    modules: Sequence[Any] = (),
) -> tuple[Any, ...]:
    """Compile every registered module against the frozen build."""
    contributions = []
    references = (
        blueprint.modules if blueprint is not None
        else _modules_from_registrations(modules)
    )
    for reference in references:
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


def create_build(
    *, languages: Sequence[Any], namespace: Any,
) -> BuildIR:
    """Lower a custom language registry into a build."""
    from ...kernel import Registry

    return Registry(languages).build(namespace)


def compile_build(
    *, build: BuildIR, modules: Sequence[Any] = (), engine: Any = None,
) -> Any:
    """Compile a custom build into an executable workflow contract."""
    from ...workflow.internal import (
        assemble_workflow, create_workflow_contract,
    )

    contributions = asyncio.run(_compile_modules(None, build, engine, modules))
    workflow = assemble_workflow(contributions)
    return create_workflow_contract(workflow, provenance=None)


def compile_workflow(
    *, blueprint: BuildBlueprint, engine: Any = None,
) -> Any:
    """Compile a blueprint's modules into an executable workflow contract."""
    from ...workflow.internal import (
        assemble_workflow, create_workflow_contract,
    )

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
    """Hash the canonical blueprint document, ignoring debug names."""
    from hashlib import sha256
    import json

    from ..internal import encode_blueprint

    document = encode_blueprint(blueprint)
    for item in document.get("binding", ()):
        item.pop("debug_name", None)
    payload = json.dumps(
        document, sort_keys=True, separators=(",", ":"), default=str,
    ).encode()
    return sha256(payload).hexdigest()


__all__ = ["compile_build", "compile_workflow", "create_build"]
