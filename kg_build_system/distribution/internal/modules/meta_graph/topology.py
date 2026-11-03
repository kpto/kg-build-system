"""Stable internal topology interface of the meta-graph module.

External module authors read the effective graph topology through this module.
The implementation stays in
:mod:`kg_build_system.distribution._private.modules.meta_graph.topology`.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from ...._private.modules.meta_graph.instruction_dto import MetaGraphComponentDTO

if TYPE_CHECKING:
    from .....declaration.blueprint.public import GraphBlueprint
    from .....declaration.languages.table.internal import StructDTO
    from .....declaration.languages.topology.internal.dto import EdgeDTO, NodeDTO
    from .....kernel.internal.types.dto import LogicalTypeDTO


def effective_components(
    blueprint: GraphBlueprint,
) -> tuple[NodeDTO | EdgeDTO, ...]:
    """The concrete and abstract components a build actually uses."""
    from ...._private.modules.meta_graph.topology import (
        effective_components as implementation,
    )

    return implementation(blueprint)


def component_entries(
    blueprint: GraphBlueprint,
) -> tuple[MetaGraphComponentDTO, ...]:
    """The effective topology entries the meta-graph document reports."""
    from ...._private.modules.meta_graph.topology import (
        component_entries as implementation,
    )

    return implementation(blueprint)


def display_type(value: LogicalTypeDTO) -> str:
    """Render a logical type in the author-facing declaration vocabulary."""
    from ...._private.modules.meta_graph.topology import (
        display_type as implementation,
    )

    return implementation(value)


def expand_type(
    value: LogicalTypeDTO,
    structs: Mapping[str, StructDTO],
    visiting: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Encode a logical type, resolving every referenced struct's members."""
    from ...._private.modules.meta_graph.topology import (
        expand_type as implementation,
    )

    return implementation(value, structs, visiting)


__all__ = [
    "MetaGraphComponentDTO",
    "component_entries",
    "display_type",
    "effective_components",
    "expand_type",
]
