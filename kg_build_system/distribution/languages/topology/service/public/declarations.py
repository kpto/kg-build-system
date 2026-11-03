"""Author-facing property and endpoint wrappers for topology declarations."""
from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar, cast

from ...model.public.declarations import property
from ..internal.endpoints import make_endpoint

if TYPE_CHECKING:
    from ...model.public.declarations import Endpoint, Node

N = TypeVar("N", bound="Node")


def endpoint(target: type[N]) -> "Endpoint[N]":
    """Name a concrete node component as an edge-binding endpoint.

    Pass the token as ``source_node=`` or ``target_node=`` to
    ``edge_binding``. A token is required when the declared side is an abstract
    category and is optional for a concrete declared side.

    Example:
        ```python
        from kg_build_system import Node, endpoint

        class SiteNode(Node):
            ...

        site = endpoint(SiteNode)
        assert site.target is SiteNode
        ```
    """
    from ...model.public.declarations import Endpoint

    return cast("Endpoint[N]", make_endpoint(target))


__all__ = ["endpoint", "property"]
