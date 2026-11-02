"""Public compile surface: blueprint composition and compilation.

The composition functions lower declarations into a blueprint and compile its
modules into a workflow contract. The blueprint aggregate, protocols, validation
and codec are :mod:`kg_build_system.compile.internal`; their mechanisms are
private.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from ..internal import (
    BlueprintModule, BuildBlueprint, CompilableModule, CompilationContext,
    ModuleCompiler,
    decode_blueprint as _decode_blueprint,
    encode_blueprint as _encode_blueprint,
    validate_blueprint as _validate_blueprint,
)


def validate_blueprint(blueprint: BuildBlueprint) -> None:
    """Reject a blueprint with no graph or with colliding symbols.

    A valid blueprint has at least one component and one binding, every symbol
    ID appears once across structs, tables, components, projections, bindings
    and sources, and each table is source-bound at most once.

    Example:
    ```python
    from kg_build_system.compile import create_blueprint, validate_blueprint

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
    from kg_build_system.compile import encode_blueprint

    document = encode_blueprint(blueprint)
    ```
    """
    return _encode_blueprint(value)


def decode_blueprint(value: dict[str, Any]) -> BuildBlueprint:
    """Decode a blueprint from the document produced by :func:`encode_blueprint`.

    Example:
    ```python
    from kg_build_system.compile import decode_blueprint

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
    from .._private.blueprint import create_blueprint as _create_blueprint

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
    from .._private.blueprint import (
        configure_blueprint_modules as _configure,
    )

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
    from .._private.pipeline import compile_workflow as _compile_workflow

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
    from .._private.pipeline import create_build as _create_build

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
    from .._private.pipeline import compile_build as _compile_build

    return _compile_build(build=build, modules=modules, engine=engine)


def compile(
    *,
    modules: Sequence[Any],
    namespace_path: str | Path | None = None,
    bindings: Iterable[Any] | None = None,
    sources: Sequence[Any] | None = None,
    blueprint: BuildBlueprint | None = None,
    engine: Any = None,
) -> Any:
    """Compile declarations into an executable workflow contract.

    This is the composition entry point: it creates or reconfigures a blueprint,
    appends the core module and compiles the result. Use the lower-level
    functions here when a caller already owns the blueprint.

    Example:
    ```python
    from kg_build_system.compile import compile
    from kg_build_system.modules import FileModule, FileModuleConfiguration, register_module

    contract = compile(
        modules=(register_module(FileModule, FileModuleConfiguration("graph.jsonl")),),
    )
    ```
    """
    from ...api import compile as _compile

    return _compile(
        modules=modules,
        namespace_path=namespace_path,
        bindings=bindings,
        sources=sources,
        blueprint=blueprint,
        engine=engine,
    )


__all__ = [
    "BlueprintModule", "BuildBlueprint", "CompilableModule",
    "CompilationContext", "ModuleCompiler", "compile", "compile_build",
    "compile_workflow", "configure_blueprint_modules", "create_blueprint",
    "create_build", "decode_blueprint", "encode_blueprint",
    "validate_blueprint",
]
