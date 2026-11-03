"""The target-neutral label carried by a graph component."""
from __future__ import annotations

from ....declaration.languages.topology.internal.dto import EdgeDTO, NodeDTO


def semantic_label(component: NodeDTO | EdgeDTO) -> str:
    """The component's label, defaulting to its graph name.

    The blueprint carries labels as their own field, so this function reads the
    semantic label without consulting a Python declaration or annotation path.
    """
    if component.labels:
        return component.labels[0]
    return component.name


__all__ = ["semantic_label"]
