"""Framework-internal and provider interface of edit-time generation.

A generation provider is an extension author: it implements ``Provider`` and
builds the ``Generated*`` tree in :mod:`kg_build_system.code_generation.ir`. A
graph author requests a generation through the names re-exported by
:mod:`kg_build_system.code_generation`.
"""
from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from pathlib import Path
from threading import Event
from typing import Any

from .command import add_generate_command as _add_generate_command
from .discovery import discover as _discover, discover_file as _discover_file
from .engine import GenerationSession, generate as _generate
from .ir import (
    GeneratedAnnotation, GeneratedArrayType, GeneratedClass, GeneratedField,
    GeneratedFile, GeneratedMember, GeneratedNullableType, GeneratedPackage,
    GeneratedScalarType, GeneratedStructType, GeneratedType, Nullability,
    NullabilityNote, ScalarTypeName, StaticValue,
)
from .models import (
    DiscoveredGeneration, Generation, GenerationAction, GenerationActionKind,
    GenerationError, GenerationLocation, GenerationManifest, GenerationRequest,
    GenerationResult, GenerationStatus,
)
from .providers import (
    Provider, ProviderContext, ProviderGenerationConfig,
    load_provider as _load_provider,
    resolve_provider_path as _resolve_provider_path,
)
from .requests import generation as _generation
from .watcher import FileChange, FileChangeKind, watch as _watch

__all__ = [
    "DiscoveredGeneration",
    "FileChange",
    "FileChangeKind",
    "GeneratedAnnotation",
    "GeneratedArrayType",
    "GeneratedClass",
    "GeneratedField",
    "GeneratedFile",
    "GeneratedMember",
    "GeneratedNullableType",
    "GeneratedPackage",
    "GeneratedScalarType",
    "GeneratedStructType",
    "GeneratedType",
    "Generation",
    "GenerationAction",
    "GenerationActionKind",
    "GenerationError",
    "GenerationLocation",
    "GenerationManifest",
    "GenerationRequest",
    "GenerationResult",
    "GenerationSession",
    "GenerationStatus",
    "Nullability",
    "NullabilityNote",
    "Provider",
    "ProviderContext",
    "ProviderGenerationConfig",
    "ScalarTypeName",
    "StaticValue",
    "add_generate_command",
    "discover",
    "discover_file",
    "generate",
    "generation",
    "load_provider",
    "resolve_provider_path",
    "watch",
]


def add_generate_command(commands: Any) -> None:
    """Register the ``generate`` command on a root CLI parser.

    ``commands`` is an ``argparse`` subparser collection. The command carries
    ``--watch``, ``--check``, ``--regenerate``, ``--project`` and ``--debounce``
    and dispatches to the generation runner.

    Example:
        ```python
        import argparse

        from kg_build_system.code_generation.interfaces import (
            add_generate_command,
        )

        parser = argparse.ArgumentParser()
        add_generate_command(parser.add_subparsers())
        ```
    """
    _add_generate_command(commands)


def discover(project_root: str | Path) -> tuple[DiscoveredGeneration, ...]:
    """Discover every generation request beneath a project root.

    Discovery parses ``__init__.py`` files without importing the author-owned
    project. Directories beginning with ``.`` and ``__pycache__`` are skipped.

    Example:
        ```python
        from kg_build_system.code_generation import discover

        requests = discover(".")
        ```
    """
    return _discover(project_root)


def discover_file(
    project_root: str | Path, source_path: str | Path,
) -> tuple[DiscoveredGeneration, ...]:
    """Discover the generation requests declared by one source file.

    ``source_path`` must be inside ``project_root``. The file is parsed
    statically, so importing it is unnecessary and a syntax error is reported
    as a :class:`GenerationError`.

    Example:
        ```python
        from kg_build_system.code_generation import discover_file

        requests = discover_file(".", "contracts/__init__.py")
        ```
    """
    return _discover_file(project_root, source_path)


async def generate(
    project_root: str | Path, *, check: bool = False, regenerate: bool = False,
) -> GenerationResult:
    """Generate or validate all requests as one desired-state pass.

    A product whose manifest still matches its request fingerprint and file
    hashes is current without observing its sources. ``regenerate`` forces
    every provider to re-observe; with ``check`` it reports that drift as
    ``STALE`` without writing.

    Example:
        ```python
        import asyncio

        from kg_build_system.code_generation import generate

        result = asyncio.run(generate("."))
        result.status
        ```
    """
    return await _generate(project_root, check=check, regenerate=regenerate)


def generation[T: ProviderGenerationConfig](
    provider: type[Provider[T]], configuration: T, /
) -> Generation[T]:
    """Declare edit-time generation intent without performing any work.

    The call validates the provider/configuration pair and returns a frozen
    value. It does not observe a source, load data, invoke a provider or write
    a file; the assignment name is the request identity.

    Example:
        ```python
        from kg_build_system.code_generation import generation
        from kg_build_system.code_generation.builtins import (
            DataContractInferenceConfig, InferDataContractProvider,
        )

        people = generation(
            InferDataContractProvider,
            DataContractInferenceConfig(
                source="../data/people.csv", mode="table",
            ),
        )
        ```
    """
    return _generation(provider, configuration)


def load_provider(
    request: object,
) -> tuple[type[Provider[ProviderGenerationConfig]], ProviderGenerationConfig]:
    """Import and validate the provider and its static configuration.

    ``request`` must be a :class:`GenerationRequest`. The provider must declare
    non-empty ``ID`` and ``VERSION``, and the requested configuration class must
    be its exact ``CONFIG_TYPE``.

    Example:
        ```python
        from kg_build_system.code_generation import discover
        from kg_build_system.code_generation.interfaces import load_provider

        request = discover(".")[0].request
        provider_type, configuration = load_provider(request)
        ```
    """
    return _load_provider(request)


def resolve_provider_path[T: ProviderGenerationConfig](
    context: ProviderContext[T], value: str,
) -> Path:
    """Resolve a provider-owned path against the request file.

    The result is an observation target, not a tracked input: it may live
    outside the project, and the engine does not watch, hash or existence-check
    it. Re-observation happens only on an explicit regeneration pass.

    Example:
        ```python
        from pathlib import Path

        from kg_build_system.code_generation.interfaces import (
            ProviderContext, ProviderGenerationConfig, resolve_provider_path,
        )

        class Config(ProviderGenerationConfig):
            source: str

        context = ProviderContext(
            Path("."), Path("contracts/__init__.py"), "people",
            Config(source="../data/people.csv"),
        )
        resolve_provider_path(context, context.config.source)
        ```
    """
    return _resolve_provider_path(context, value)


async def watch(
    root: str | Path,
    *,
    debounce: int = 300,
    step: int = 50,
    suffixes: Iterable[str] = (".py", ".json", ".toml", ".yaml", ".yml"),
    stop_event: Event | None = None,
) -> AsyncIterator[tuple[FileChange, ...]]:
    """Yield non-empty batches of relevant changes beneath ``root``.

    ``debounce`` and ``step`` are milliseconds and must be greater than zero.
    A suffix without a leading dot is normalised. Ignored directories such as
    ``.git``, ``.venv`` and ``__pycache__`` are never reported.

    Example:
        ```python
        import asyncio

        from kg_build_system.code_generation import watch

        async def print_changes() -> None:
            async for batch in watch("."):
                print(batch)

        asyncio.run(print_changes())
        ```
    """
    async for batch in _watch(
        root, debounce=debounce, step=step, suffixes=suffixes,
        stop_event=stop_event,
    ):
        yield batch
