"""Stable internal topology interface of the meta-graph executor.

External extension authors read the effective graph topology through this
module. The implementation stays in
:mod:`kg_build_system.distribution.executors.meta_graph.service._private.topology`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
    from kg_build_system.distribution.languages.topology.model.internal.dto import (
        EdgeDTO,
        NodeDTO,
    )


def effective_components(
    blueprint: GraphBlueprint,
) -> tuple[NodeDTO | EdgeDTO, ...]:
    """The concrete and abstract components a build actually uses."""
    from .._private.topology import effective_components as implementation

    return implementation(blueprint)


__all__ = ["effective_components"]
