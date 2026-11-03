"""Author-facing file-watch values."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class FileChangeKind(StrEnum):
    """The kind of filesystem change a watcher batch reports.

    Example:
        ```python
        from kg_build_system.generation.code_generation import FileChangeKind

        FileChangeKind.MODIFIED
        ```
    """

    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"


@dataclass(frozen=True, slots=True)
class FileChange:
    """One relevant file change beneath a watched root.

    ``path`` is relative to the watched root, with the same suffix set the
    watcher accepted.

    Example:
        ```python
        from pathlib import Path

        from kg_build_system.generation.code_generation import FileChange, FileChangeKind

        change = FileChange(FileChangeKind.MODIFIED, Path("contracts/__init__.py"))
        ```
    """

    kind: FileChangeKind
    path: Path


__all__ = ["FileChange", "FileChangeKind"]
