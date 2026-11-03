"""Configuration of the meta-graph description target."""
from __future__ import annotations

from dataclasses import dataclass

from kg_build_system.distribution.model.public.paths import validate_relative_path


@dataclass(frozen=True, slots=True)
class MetaGraphConfiguration:
    """Where the document lands, and how much of the data it may quote.

    ``example_limit`` bounds the example values quoted per property;
    ``include_html`` also writes a self-contained page at
    ``html_relative_path``. Both paths stay beneath the build output directory.

    Example:
        ```python
        from kg_build_system.distribution.executors.meta_graph import (
            MetaGraphConfiguration,
        )

        configuration = MetaGraphConfiguration(example_limit=5)
        assert configuration.relative_path == "meta_graph.json"
        ```
    """

    relative_path: str = "meta_graph.json"
    example_limit: int = 3
    include_html: bool = True
    html_relative_path: str = "meta_graph.html"

    def __post_init__(self) -> None:
        validate_relative_path(
            self.relative_path, context="meta-graph document path",
        )
        validate_relative_path(
            self.html_relative_path, context="meta-graph HTML path",
        )
        if self.example_limit < 0:
            raise ValueError("meta-graph example limit may not be negative")


__all__ = ["MetaGraphConfiguration"]
