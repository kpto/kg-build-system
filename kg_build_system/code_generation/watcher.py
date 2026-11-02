"""Project file watching for edit-time generation."""
from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from threading import Event

from watchfiles import Change, awatch as _watchfiles


class FileChangeKind(StrEnum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"


@dataclass(frozen=True, slots=True)
class FileChange:
    kind: FileChangeKind
    path: Path


_IGNORED_DIRECTORIES = frozenset({
    ".git", ".hg", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
    ".venv", "__pycache__",
})

_CHANGE_KINDS = {
    Change.added: FileChangeKind.CREATED,
    Change.modified: FileChangeKind.MODIFIED,
    Change.deleted: FileChangeKind.DELETED,
}

_CHANGE_PRIORITY = {
    FileChangeKind.DELETED: 0,
    FileChangeKind.CREATED: 1,
    FileChangeKind.MODIFIED: 2,
}


async def watch(
    root: str | Path,
    *,
    debounce: int = 300,
    step: int = 50,
    suffixes: Iterable[str] = (".py", ".json", ".toml", ".yaml", ".yml"),
    stop_event: Event | None = None,
) -> AsyncIterator[tuple[FileChange, ...]]:
    """Yield non-empty batches of relevant changes beneath ``root``."""
    project_root = Path(root).resolve()
    if not project_root.is_dir():
        raise ValueError(f"watch root is not a directory: {project_root}")
    if debounce <= 0 or step <= 0:
        raise ValueError("watch debounce and step must be greater than zero")

    watched_suffixes = frozenset(
        suffix if suffix.startswith(".") else f".{suffix}" for suffix in suffixes
    )

    def relevant(_change: Change, changed_path: str) -> bool:
        path = Path(changed_path)
        try:
            relative = path.resolve().relative_to(project_root)
        except ValueError:
            return False
        return path.suffix in watched_suffixes and not any(
            part in _IGNORED_DIRECTORIES for part in relative.parts
        )

    async for batch in _watchfiles(
        project_root,
        watch_filter=relevant,
        debounce=debounce,
        step=step,
        stop_event=stop_event,
        raise_interrupt=False,
    ):
        by_path: dict[Path, FileChangeKind] = {}
        for change, path in batch:
            relative = Path(path).resolve().relative_to(project_root)
            kind = _CHANGE_KINDS[change]
            previous = by_path.get(relative)
            if previous is None or _CHANGE_PRIORITY[kind] > _CHANGE_PRIORITY[previous]:
                by_path[relative] = kind
        changes = tuple(
            FileChange(by_path[path], path)
            for path in sorted(by_path, key=lambda value: value.as_posix())
        )
        if changes:
            yield changes


__all__ = ["FileChange", "FileChangeKind", "watch"]
