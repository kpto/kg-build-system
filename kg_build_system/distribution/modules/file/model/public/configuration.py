"""Configuration of the JSON Lines file target."""
from __future__ import annotations

from dataclasses import dataclass

from kg_build_system.distribution.model.public.paths import validate_relative_path


@dataclass(frozen=True, slots=True)
class FileConfiguration:
    """Where the graph file is written, beneath the build output directory.

    ``relative_path`` is validated by the distribution relative-path rule and
    may be replaced at runtime through the component's ``relative_path`` runtime
    field.

    Example:
        ```python
        from kg_build_system.distribution.modules.file import FileConfiguration

        configuration = FileConfiguration("graph.jsonl")
        assert configuration.relative_path == "graph.jsonl"
        ```
    """

    relative_path: str

    def __post_init__(self) -> None:
        validate_relative_path(self.relative_path, context="file output path")


__all__ = ["FileConfiguration"]
