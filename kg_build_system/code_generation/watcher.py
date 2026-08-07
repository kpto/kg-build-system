"""Project file watching for the code-generation PoC."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from threading import Event

from watchfiles import Change, watch as _watchfiles


class FileChangeKind(StrEnum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"


@dataclass(frozen=True, slots=True)
class FileChange:
    kind: FileChangeKind
    path: Path


_IGNORED_DIRECTORIES = frozenset(
    {".git", ".hg", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".venv", "__pycache__"}
)


_CHANGE_KINDS = {
    Change.added: FileChangeKind.CREATED,
    Change.modified: FileChangeKind.MODIFIED,
    Change.deleted: FileChangeKind.DELETED,
}


def watch(
    root: str | Path,
    *,
    debounce: int = 300,
    step: int = 50,
    suffixes: Iterable[str] = (".py", ".json", ".toml", ".yaml", ".yml"),
    stop_event: Event | None = None,
) -> Iterator[tuple[FileChange, ...]]:
    """Yield non-empty batches of relevant changes beneath ``root``."""
    project_root = Path(root).resolve()
    if not project_root.is_dir():
        raise ValueError(f"watch root is not a directory: {project_root}")
    if debounce <= 0 or step <= 0:
        raise ValueError("watch debounce and step must be greater than zero")

    watched_suffixes = frozenset(suffix if suffix.startswith(".") else f".{suffix}" for suffix in suffixes)

    def relevant(_change: Change, changed_path: str) -> bool:
        path = Path(changed_path)
        try:
            relative = path.resolve().relative_to(project_root)
        except ValueError:
            return False
        return path.suffix in watched_suffixes and not any(
            part in _IGNORED_DIRECTORIES for part in relative.parts
        )

    for batch in _watchfiles(
        project_root,
        watch_filter=relevant,
        debounce=debounce,
        step=step,
        stop_event=stop_event,
        raise_interrupt=False,
    ):
        changes = tuple(
            sorted(
                (
                    FileChange(_CHANGE_KINDS[change], Path(path).resolve().relative_to(project_root))
                    for change, path in batch
                ),
                key=lambda item: item.path.as_posix(),
            )
        )
        if changes:
            yield changes
