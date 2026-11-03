"""Author-facing generation outcome values."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class GenerationStatus(StrEnum):
    """The outcome of comparing a desired product with what is installed.

    ``CURRENT`` means no product needs writing; ``CHANGED`` means the desired
    state differs and was written (or would be written); ``STALE`` is reported
    by ``check`` when products are missing, altered or orphaned.

    Example:
        ```python
        import asyncio

        from kg_build_system.generation.code_generation import generate

        result = asyncio.run(generate(".", check=True))
        result.status in {"current", "stale"}
        ```
    """

    CURRENT = "current"
    CHANGED = "changed"
    STALE = "stale"


class GenerationActionKind(StrEnum):
    """The kind of declaration change observed by watch mode.

    Example:
        ```python
        from kg_build_system.generation.code_generation.model.public import (
            GenerationActionKind,
        )

        GenerationActionKind.DECLARATION_ADDED
        ```
    """

    DECLARATION_ADDED = "declaration_added"
    DECLARATION_CHANGED = "declaration_changed"
    DECLARATION_DELETED = "declaration_deleted"


@dataclass(frozen=True, slots=True)
class GenerationAction:
    """A watched input change and the declaration modules affected by it.

    ``source_paths`` are the declaration files to regenerate;
    ``declaration_id`` is the generated package import when the action concerns
    one request.

    Example:
        ```python
        from pathlib import Path

        from kg_build_system.generation.code_generation.model.public import (
            GenerationAction, GenerationActionKind,
        )

        action = GenerationAction(
            GenerationActionKind.DECLARATION_ADDED,
            Path("contracts/__init__.py"),
            (Path("contracts/__init__.py"),),
            "contracts.people",
        )
        ```
    """

    kind: GenerationActionKind
    trigger_path: Path
    source_paths: tuple[Path, ...]
    declaration_id: str | None = None


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """The outcome of one generation or check pass.

    Paths are relative to the project root. ``actions`` is populated by watch
    mode; ``diagnostics`` explains a ``STALE`` or failed comparison.

    Example:
        ```python
        import asyncio

        from kg_build_system.generation.code_generation import generate

        result = asyncio.run(generate("."))
        result.created_paths
        ```
    """

    status: GenerationStatus
    changed_paths: tuple[Path, ...] = ()
    created_paths: tuple[Path, ...] = ()
    updated_paths: tuple[Path, ...] = ()
    deleted_paths: tuple[Path, ...] = ()
    diagnostics: tuple[str, ...] = ()
    actions: tuple[GenerationAction, ...] = ()


__all__ = [
    "GenerationAction", "GenerationActionKind", "GenerationResult",
    "GenerationStatus",
]
