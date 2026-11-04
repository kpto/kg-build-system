"""Path rules shared by distribution executors and their configurations."""
from __future__ import annotations

from pathlib import Path


def validate_relative_path(value: str, *, context: str) -> None:
    """Reject any path that could escape the build output directory."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be a non-empty relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(
            f"{context} must be relative to the build output directory"
        )


__all__ = ["validate_relative_path"]
