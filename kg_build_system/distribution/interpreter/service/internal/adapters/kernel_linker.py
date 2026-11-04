"""The kernel ``Linker`` protocol implemented for graph blueprints."""
from __future__ import annotations

from collections.abc import Sequence

from kg_build_system.kernel import Language, Namespace

from ....model.public import GraphBlueprint
from ..link import link_blueprint


class BlueprintLinker:
    """Link expression, data, topology and binding declarations into a blueprint.

    The linker discovers each language's declarations, transcribes them in the
    fixed order ``expressions``, ``data``, ``topology``, ``binding``, resolves
    every symbol reference and assembles the blueprint.

    Example:
        ```python
        from kg_build_system.distribution.interpreter.service.internal import (
            BlueprintLinker,
        )

        linker = BlueprintLinker()
        blueprint = linker.link(languages, namespace)
        ```
    """

    def link(
        self, languages: Sequence[Language], namespace: Namespace,
    ) -> GraphBlueprint:
        """Assemble and validate a blueprint from the language declarations.

        Example:
            ```python
            blueprint = BlueprintLinker().link(languages, namespace)
            ```
        """
        return link_blueprint(languages, namespace)


__all__ = ["BlueprintLinker"]
