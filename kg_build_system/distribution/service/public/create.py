"""Create a graph blueprint from declarations.

The distribution facade exposes blueprint creation beside its planners and
executors; the implementation lives in the graph interpreter.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from ...interpreter.model.public import GraphBlueprint

if TYPE_CHECKING:
    from kg_build_system.distribution.languages.binding.model.public import (
        Binding,
    )
    from kg_build_system.kernel import Language


def create_blueprint(
    *,
    namespace_path: str | Path | None = None,
    bindings: Iterable[Binding] = (),
    languages: Sequence[Language] | None = None,
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
        languages=languages,
    )


__all__ = ["create_blueprint"]
