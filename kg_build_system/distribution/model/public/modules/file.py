"""The JSON Lines file target's configuration."""
from __future__ import annotations

from dataclasses import dataclass

from ..paths import validate_relative_path
from ..registration import ModuleRegistrationConfiguration


@dataclass(frozen=True)
class FileModuleConfiguration(ModuleRegistrationConfiguration):
    """Where the graph file is written, beneath the build output directory.

    ``relative_path`` must stay inside the output directory. The runtime field
    ``relative_path`` may replace it for one build.

    Example:
        ```python
        from kg_build_system.distribution import (
            FileModule, FileModuleConfiguration, register_module,
        )

        modules = (
            register_module(
                FileModule, FileModuleConfiguration("graph.jsonl"),
            ),
        )
        ```
    """

    relative_path: str

    def __post_init__(self) -> None:
        validate_relative_path(self.relative_path, context="file output path")


__all__ = ["FileModuleConfiguration"]
