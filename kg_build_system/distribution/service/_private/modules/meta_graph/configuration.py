"""Validation of the meta-graph module configuration."""
from __future__ import annotations

from ...service.paths import validate_relative_path


def validate(
    *,
    relative_path: str,
    html_relative_path: str,
    example_limit: int,
) -> None:
    """Reject an output path outside the build and a negative example limit."""
    validate_relative_path(relative_path, context="meta-graph document path")
    validate_relative_path(html_relative_path, context="meta-graph HTML path")
    if example_limit < 0:
        raise ValueError("meta-graph example limit may not be negative")


__all__ = ["validate"]
