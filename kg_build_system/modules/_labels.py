"""Shared reading of the target-neutral label carried by a graph component."""
from __future__ import annotations

from .._frozen_json import thaw_json
from ..annotations.interfaces import EdgeLabel, NodeLabel
from ..topology.ir import ComponentIR


def semantic_label(component: ComponentIR) -> str:
    """The component's semantic label, defaulting to its logical name.

    Reading the label is target-neutral; translating it into a target's native
    vocabulary stays with that target. Label uniqueness is already enforced at
    class creation, so the checks here backstop a blueprint decoded from JSON
    rather than guard an authored declaration.
    """
    expected, opposite = (
        (NodeLabel, EdgeLabel) if component.kind == "node"
        else (EdgeLabel, NodeLabel)
    )
    mismatched = [
        item for item in component.annotations
        if item.namespace == opposite.namespace
        and item.annotation_id == opposite.annotation_id
    ]
    if mismatched:
        raise ValueError(
            f"{component.kind} component {component.name!r} has an incompatible "
            f"{opposite.__name__} annotation"
        )
    matches = [
        item for item in component.annotations
        if item.namespace == expected.namespace
        and item.annotation_id == expected.annotation_id
    ]
    if len(matches) > 1:
        raise ValueError(
            f"{component.kind} component {component.name!r} accepts at most one "
            f"{expected.__name__} annotation"
        )
    if not matches:
        return component.name
    arguments = thaw_json(matches[0].arguments)
    if not isinstance(arguments, dict) or set(arguments) != {"label"}:
        raise ValueError(f"{expected.__name__} has invalid serialized arguments")
    label = arguments["label"]
    if not isinstance(label, str) or not label.strip():
        raise ValueError(f"{expected.__name__} label must be a non-empty string")
    return label


__all__ = ["semantic_label"]
