"""Working and temporary storage used by a workflow execution."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ....model.public.services import WorkingStorage


@dataclass(frozen=True, slots=True)
class LocalWorkingStorage:
    """Working storage implemented as paths beneath one root."""

    root: Path

    def child(self, relative_path: PurePosixPath) -> Path:
        """Resolve one relative path beneath the root."""
        return self.root.joinpath(*relative_path.parts)


@dataclass(frozen=True, slots=True)
class LocalTemporaryStorage:
    """Temporary storage implemented as one root directory."""

    root: Path


__all__ = ["LocalTemporaryStorage", "LocalWorkingStorage", "WorkingStorage"]
