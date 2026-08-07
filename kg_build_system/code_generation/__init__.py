"""Edit-time code-generation support."""

from .watcher import FileChange, FileChangeKind, watch

__all__ = ["FileChange", "FileChangeKind", "watch"]
