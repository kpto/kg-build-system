"""Endpoint-token construction interface for topology declarations."""
from __future__ import annotations

from typing import Any


def make_endpoint(target: type[object]) -> Any:
    """Validate a concrete node class and return its endpoint token."""
    from .._private.class_creation import make_endpoint as build

    return build(target)


__all__ = ["make_endpoint"]
