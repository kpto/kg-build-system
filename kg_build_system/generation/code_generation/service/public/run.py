"""Author-facing discovery, generation and watch wrappers."""
from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from pathlib import Path
from threading import Event

from ...model.public import FileChange, GenerationResult
from ...model.internal.models import DiscoveredGeneration
from .session import GenerationSession


def discover(project_root: str | Path) -> tuple[DiscoveredGeneration, ...]:
    """Discover every asset contract beneath a project root.

    Discovery parses Python files without importing the author-owned project.
    Directories beginning with ``.`` and ``__pycache__`` are skipped. A request's
    identity is its asset name and its product is ``<package>/<asset name>``.

    Example:
        ```python
        from kg_build_system.generation.code_generation import discover

        requests = discover(".")
        ```
    """
    from .._private.discovery import discover as implementation

    return implementation(project_root)


def discover_file(
    project_root: str | Path, source_path: str | Path,
) -> tuple[DiscoveredGeneration, ...]:
    """Discover the asset contracts declared by one source file.

    ``source_path`` must be inside ``project_root``. The file is parsed
    statically, so importing it is unnecessary and a syntax error is reported
    as a :class:`GenerationError`.

    Example:
        ```python
        from kg_build_system.generation.code_generation import discover_file

        requests = discover_file(".", "contracts/assets.py")
        ```
    """
    from .._private.discovery import discover_file as implementation

    return implementation(project_root, source_path)


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

        from kg_build_system.generation.code_generation import generate

        result = asyncio.run(generate("."))
        result.status
        ```
    """
    from .._private.engine import generate as implementation

    return await implementation(project_root, check=check, regenerate=regenerate)


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

        from kg_build_system.generation.code_generation import watch

        async def print_changes() -> None:
            async for batch in watch("."):
                print(batch)

        asyncio.run(print_changes())
        ```
    """
    from .._private.watcher import watch as implementation

    async for batch in implementation(
        root, debounce=debounce, step=step, suffixes=suffixes,
        stop_event=stop_event,
    ):
        yield batch


__all__ = ["GenerationSession", "discover", "discover_file", "generate", "watch"]
