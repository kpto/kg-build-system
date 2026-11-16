"""Endpoint-token construction interface for topology declarations."""
from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from ...model.public.declarations import Endpoint, Node


def make_endpoint[N: Node](target: type[N]) -> "Endpoint[N]":
    """Validate a concrete node class and return its endpoint token."""
    from .._private.class_creation import make_endpoint as build

    return cast("Endpoint[N]", build(target))


__all__ = ["make_endpoint"]
