"""Internal compilation interface.

The interface exposes frozen blueprint data, the module compiler protocols and
thin wrappers over the compilation pipeline. The wrappers keep the implementation
in :mod:`kg_build_system.compile.pipeline` private and import it on first use, so
the pipeline may depend on this module without a circular import.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, Protocol

from ..kernel.contract import CompilationContext
from .ir import BlueprintModule, BuildBlueprint


class ModuleCompiler(Protocol):
    async def compile(self, context: Any) -> Any: ...


class CompilableModule(Protocol):
    ID: str
    VERSION: str
    CONFIGURATION_TYPE: type[Any]

    @classmethod
    async def create_compiler(cls, context: Any) -> ModuleCompiler: ...


def _validate_blueprint(blueprint: BuildBlueprint) -> None:
    if not blueprint.components:
        raise ValueError("blueprints require at least one graph component")
    if not blueprint.bindings:
        raise ValueError("blueprints require at least one graph binding")
    symbols = (
        *(item.symbol_id for item in blueprint.structs),
        *(item.symbol_id for item in blueprint.tables),
        *(item.symbol_id for item in blueprint.components),
        *(item.symbol_id for item in blueprint.projections),
        *(item.symbol_id for item in blueprint.bindings),
        *(item.symbol_id for item in blueprint.sources),
    )
    if len(symbols) != len(set(symbols)):
        raise ValueError("blueprint symbol IDs must be unique")
    sources = tuple(item.table for item in blueprint.sources)
    if len(sources) != len(set(sources)):
        raise ValueError("source-bound table names must be unique")


def _encode_blueprint(value: BuildBlueprint) -> dict[str, Any]:
    from ..binding.interfaces import encode_binding_part
    from ..table.interfaces import encode_data_part
    from ..table.ir import DataIR
    from ..topology.interfaces import encode_topology_part

    return {
        "data": encode_data_part(DataIR(
            value.structs, value.tables, value.projections, value.sources,
        )),
        "topology": encode_topology_part(value.components),
        "binding": encode_binding_part(value.bindings),
        "modules": [
            {
                "module_id": item.module_id,
                "module_import": item.module_import,
                "module_qualname": item.module_qualname,
                "configuration": item.configuration,
            }
            for item in value.modules
        ],
    }


def _decode_blueprint(value: dict[str, Any]) -> BuildBlueprint:
    from ..table.interfaces import decode_data_part
    from ..topology.interfaces import decode_topology_part
    from ..binding.interfaces import decode_binding_part

    data = decode_data_part(value["data"])
    components = decode_topology_part(value["topology"])
    bindings = decode_binding_part(value["binding"])
    modules = tuple(
        BlueprintModule(
            item["module_id"], item["module_import"], item["module_qualname"],
            item.get("configuration"),
        )
        for item in value.get("modules", ())
    )
    return BuildBlueprint(
        data.structs, data.tables, components, data.projections, bindings,
        data.sources, modules,
    )


def validate_blueprint(blueprint: BuildBlueprint) -> None:
    """Reject a blueprint with no graph or with colliding symbols.

    A valid blueprint has at least one component and one binding, every symbol
    ID appears once across structs, tables, components, projections, bindings
    and sources, and each table is source-bound at most once.

    Example:
    ```python
    from kg_build_system.compile import create_blueprint
    from kg_build_system.compile.interfaces import validate_blueprint

    blueprint = create_blueprint(namespace_path="graph_pipeline")
    validate_blueprint(blueprint)
    ```
    """
    _validate_blueprint(blueprint)


def encode_blueprint(value: BuildBlueprint) -> dict[str, Any]:
    """Encode a blueprint into its canonical JSON-compatible document.

    The document has ``data``, ``topology``, ``binding`` and ``modules`` parts,
    in the same shape :func:`decode_blueprint` accepts.

    Example:
    ```python
    from kg_build_system.compile.interfaces import encode_blueprint

    document = encode_blueprint(blueprint)
    ```
    """
    return _encode_blueprint(value)


def decode_blueprint(value: dict[str, Any]) -> BuildBlueprint:
    """Decode a blueprint from the document produced by :func:`encode_blueprint`.

    Example:
    ```python
    from kg_build_system.compile.interfaces import decode_blueprint

    blueprint = decode_blueprint(document)
    ```
    """
    return _decode_blueprint(value)


def create_blueprint(
    *,
    bindings: Iterable[Any] = (),
    sources: Sequence[Any] = (),
    modules: Sequence[Any] = (),
    namespace_path: str | Path | None = None,
    languages: Sequence[Any] | None = None,
) -> BuildBlueprint:
    """Collect declarations into a validated, frozen blueprint.

    Supply either ``namespace_path`` or both ``bindings`` and ``sources``; the
    default languages are the table, topology and binding languages.

    Example:
    ```python
    from pathlib import Path

    from kg_build_system.compile import create_blueprint

    blueprint = create_blueprint(namespace_path=Path("graph_pipeline"))
    ```
    """
    from .pipeline import create_blueprint as _create_blueprint

    return _create_blueprint(
        bindings=bindings,
        sources=sources,
        modules=modules,
        namespace_path=namespace_path,
        languages=languages,
    )


def configure_blueprint_modules(
    blueprint: BuildBlueprint, modules: Sequence[Any],
) -> BuildBlueprint:
    """Return a blueprint with its module composition replaced.

    The declarations and the module references are copied; the supplied module
    registrations provide the new ``modules`` tuple.

    Example:
    ```python
    from kg_build_system.compile import configure_blueprint_modules

    configured = configure_blueprint_modules(blueprint, modules)
    ```
    """
    from .pipeline import configure_blueprint_modules as _configure

    return _configure(blueprint, modules)


def compile_workflow(
    *, blueprint: BuildBlueprint, engine: Any = None,
) -> Any:
    """Compile a blueprint's modules into a frozen workflow contract.

    The blueprint supplies the declarations; each module compiler contributes
    its steps, and the assembler resolves their connections. No source is read.

    Example:
    ```python
    from kg_build_system.compile import compile_workflow

    contract = compile_workflow(blueprint=blueprint)
    ```
    """
    from .pipeline import compile_workflow as _compile_workflow

    return _compile_workflow(blueprint=blueprint, engine=engine)


def create_build(
    *, languages: Sequence[Any], namespace: Any,
) -> Any:
    """Lower a custom language registry into a build, without a blueprint.

    Use this when a custom language composition replaces the default table,
    topology and binding languages.

    Example:
    ```python
    from kg_build_system.compile import create_build

    build = create_build(languages=(EchoLanguage(),), namespace=namespace)
    ```
    """
    from .pipeline import create_build as _create_build

    return _create_build(languages=languages, namespace=namespace)


def compile_build(
    *, build: Any, modules: Sequence[Any] = (), engine: Any = None,
) -> Any:
    """Compile a custom build with modules that read its language parts.

    The modules are loaded from their registered references and contribute
    steps to the assembled workflow.

    Example:
    ```python
    from kg_build_system.compile import compile_build

    contract = compile_build(build=build, modules=modules)
    ```
    """
    from .pipeline import compile_build as _compile_build

    return _compile_build(build=build, modules=modules, engine=engine)


__all__ = [
    "BlueprintModule", "BuildBlueprint", "CompilableModule", "CompilationContext",
    "ModuleCompiler", "compile_build", "compile_workflow",
    "configure_blueprint_modules", "create_blueprint", "create_build",
    "decode_blueprint", "encode_blueprint", "validate_blueprint",
]
