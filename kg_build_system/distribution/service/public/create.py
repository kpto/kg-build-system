"""Create a graph blueprint from declarations.

The distribution facade exposes blueprint creation beside its planners and
executors; the implementation lives in the graph interpreter.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from ...interpreter.model.public import GraphBlueprint


def create_blueprint(
    *,
    namespace_path: str | Path | None = None,
    bindings: Iterable[Any] = (),
    sources: Sequence[Any] = (),
    languages: Sequence[Any] | None = None,
) -> GraphBlueprint:
    """Collect declarations into a validated, frozen graph blueprint.

    Example:
        ```python
        from pathlib import Path

        from kg_build_system.distribution import create_blueprint

        blueprint = create_blueprint(namespace_path=Path("graph_pipeline"))
        ```
    """
    from ...interpreter.service.public import create_blueprint as implementation

    return implementation(
        namespace_path=namespace_path,
        bindings=bindings,
        sources=sources,
        languages=languages,
    )


__all__ = ["create_blueprint"]
