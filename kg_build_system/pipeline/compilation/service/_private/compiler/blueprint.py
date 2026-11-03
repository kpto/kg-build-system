"""Read a graph blueprint into the kernel's in-memory build.

Compilation never creates a blueprint. It accepts the one it was given and
decomposes it into one named part per language; module compilers read those parts
through ``CompilationContext.build`` and the blueprint itself through the same
context.
"""
from __future__ import annotations

from kg_build_system.declaration.blueprint.model.public import GraphBlueprint
from ......kernel import Build


def decompose(blueprint: GraphBlueprint) -> Build:
    """Return the in-memory build the blueprint describes.

    The parts are the blueprint's own layer DTOs: the data part, the topology
    graph, the bindings and the physical sources. No authoring state is added.

    Example:
    ```python
    from kg_build_system.pipeline.compilation.service.internal import decompose

    build = decompose(blueprint)
    ```
    """
    return Build({
        "data": blueprint.data,
        "topology": blueprint.graph,
        "binding": blueprint.bindings,
        "sources": blueprint.sources,
    })


__all__ = ["GraphBlueprint", "decompose"]
