"""Read a graph blueprint into the kernel's in-memory build.

Compilation never creates a blueprint. It accepts the one it was given and
decomposes it into one named part per language; the decomposition mechanism
lives in ``_private``.
"""
from __future__ import annotations

from kg_build_system.declaration.blueprint.model.public import GraphBlueprint
from ......kernel import Build


def decompose(blueprint: GraphBlueprint) -> Build:
    """Return the in-memory build the blueprint describes."""
    from ..._private.compiler.blueprint import decompose as _decompose

    return _decompose(blueprint)


__all__ = ["GraphBlueprint", "decompose"]
