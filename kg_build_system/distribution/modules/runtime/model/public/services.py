"""Runtime capabilities shared by distribution step executors."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Protocol


class WorkflowLogger(Protocol):
    """Step-scoped logging exposed to instruction executors."""

    def debug(self, message: str, *args: object) -> None:
        """Log one debug message."""
        ...

    def info(self, message: str, *args: object) -> None:
        """Log one informational message."""
        ...

    def warning(self, message: str, *args: object) -> None:
        """Log one warning."""
        ...

    def error(self, message: str, *args: object) -> None:
        """Log one error."""
        ...


class NullWorkflowLogger:
    """A logger that discards every message."""

    def debug(self, message: str, *args: object) -> None:
        pass

    def info(self, message: str, *args: object) -> None:
        pass

    def warning(self, message: str, *args: object) -> None:
        pass

    def error(self, message: str, *args: object) -> None:
        pass


class WorkingStorage(Protocol):
    """Storage rooted at a caller-selected workflow directory."""

    def child(self, relative_path: PurePosixPath) -> Path:
        """Resolve one relative path beneath the root."""
        ...


class OutputStorage(Protocol):
    """Storage rooted at the build's output directory."""

    def child(self, relative_path: PurePosixPath) -> Path:
        """Resolve one relative path beneath the root.

        Example:
            ```python
            path = storage.child(PurePosixPath("graph.jsonl"))
            ```
        """
        ...


class TemporaryStorage(Protocol):
    """Temporary storage implemented as one owned root directory."""

    @property
    def root(self) -> Path:
        """The root directory this execution owns and removes."""
        ...


class CredentialResolver(Protocol):
    """Resolve a credential reference to its value."""

    def resolve(self, reference: str) -> str:
        """Resolve one credential reference."""
        ...


__all__ = [
    "CredentialResolver",
    "NullWorkflowLogger",
    "OutputStorage",
    "TemporaryStorage",
    "WorkingStorage",
    "WorkflowLogger",
]
