"""The kernel ``Linker`` protocol implemented for graph blueprints."""
from __future__ import annotations

from collections.abc import Mapping

from kg_build_system.kernel import Layer

from ....model.public import GraphBlueprint
from ..assembly import assemble_blueprint
from ..validation import validate_blueprint


class BlueprintLinker:
    """Link the data, topology and binding layers into one graph blueprint.

    Example:
        ```python
        from kg_build_system.distribution.interpreter.service.internal import (
            BlueprintLinker,
        )

        linker = BlueprintLinker()
        assert linker.requires == ("data", "topology", "binding")
        ```
    """

    requires: tuple[str, ...] = ("data", "topology", "binding")

    def link(self, layers: Mapping[str, Layer]) -> GraphBlueprint:
        """Assemble and validate a blueprint from the three linked layers.

        Example:
            ```python
            blueprint = BlueprintLinker().link(layers)
            ```
        """
        graph = layers["topology"].value
        data = layers["data"].value
        bindings = layers["binding"].value
        blueprint = assemble_blueprint(graph, data, bindings)
        validate_blueprint(blueprint)
        return blueprint


__all__ = ["BlueprintLinker"]
