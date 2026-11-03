"""Create a graph blueprint from declarations."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from ...model.public import GraphBlueprint


def create_blueprint(
    *,
    namespace_path: str | Path | None = None,
    bindings: Iterable[Any] = (),
    sources: Sequence[Any] = (),
    languages: Sequence[Any] | None = None,
) -> GraphBlueprint:
    """Collect declarations into a validated, frozen graph blueprint.

    Supply either ``namespace_path`` or explicit ``bindings`` and ``sources``.
    The declared languages are run through the kernel toolchain; each language
    collects and transcribes its own DTO, and :class:`BlueprintLinker` assembles
    the DTOs into one blueprint.

    Example:
    ```python
    from pathlib import Path

    from kg_build_system.distribution.interpreter import create_blueprint

    blueprint = create_blueprint(namespace_path=Path("graph_pipeline"))
    ```
    """
    from .._private.create import create_blueprint as implementation

    return implementation(
        namespace_path=namespace_path,
        bindings=bindings,
        sources=sources,
        languages=languages,
    )


__all__ = ["create_blueprint"]
