"""Author-facing incremental generation session."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from ...model.public import GenerationResult
from ...model.public.results import GenerationAction


class GenerationSession:
    """Complete baseline and declaration index for incremental watch mode.

    A session runs an initial desired-state pass, then compares each watched
    declaration edit with the indexed request set. Only a changed request causes
    a generation pass; product files are ignored.

    Example:
        ```python
        from kg_build_system.generation.code_generation import GenerationSession

        session = GenerationSession(".")
        ```
    """

    def __init__(self, project_root: str | Path) -> None:
        """Index the project root, without generating or observing anything yet.

        Call :meth:`start` for the baseline pass and :meth:`handle` for each
        watched change batch.

        Example:
            ```python
            from kg_build_system.generation.code_generation import GenerationSession

            session = GenerationSession(".")
            ```
        """
        from .._private.engine import GenerationSession as implementation

        self._session: Any = implementation(project_root)

    async def start(self) -> GenerationResult:
        """Run the baseline generation pass and index the resulting requests.

        The returned result describes what the initial pass wrote; subsequent
        changes are handled by :meth:`handle`.

        Example:
            ```python
            import asyncio

            from kg_build_system.generation.code_generation import GenerationSession

            async def run() -> None:
                session = GenerationSession(".")
                result = await session.start()
                print(result.status)

            asyncio.run(run())
            ```
        """
        return await self._session.start()

    async def handle(
        self,
        changed_paths: Iterable[str | Path],
        *,
        on_action: Callable[[GenerationAction], None] | None = None,
    ) -> GenerationResult:
        """Regenerate after a batch of watched declaration changes.

        Paths may be absolute or relative to the project root. Only changed
        ``__init__.py`` request declarations schedule a pass; paths beneath an
        owned product are ignored. ``on_action`` receives each added, changed
        or deleted declaration before generation runs.

        Example:
            ```python
            import asyncio
            from pathlib import Path

            from kg_build_system.generation.code_generation import GenerationSession

            async def run() -> None:
                session = GenerationSession(".")
                await session.start()
                result = await session.handle(
                    [Path("contracts/__init__.py")],
                    on_action=lambda action: print(action.kind),
                )
                print(result.actions)

            asyncio.run(run())
            ```
        """
        return await self._session.handle(changed_paths, on_action=on_action)


__all__ = ["GenerationSession"]
