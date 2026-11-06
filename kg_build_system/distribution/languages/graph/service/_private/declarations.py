"""Prepare a ``Graph`` subclass for discovery and transcription."""
from __future__ import annotations

from typing import Any, TypeGuard

from kg_build_system.distribution.service.internal.rendering import snake_case

from ...model.public.options import GraphOptions


def prepare_graph_declaration(cls: type[Any]) -> None:
    """Validate and record the options and name of a graph subclass."""
    options = vars(cls).get("options")
    if not isinstance(options, GraphOptions):
        raise TypeError(
            f"graph {cls.__name__!r} must declare options = GraphOptions(...)"
        )
    name = options.name or snake_case(cls.__name__)
    if not name:
        raise ValueError(f"graph {cls.__name__!r} has no usable name")
    cls._graph_options = options
    cls._graph_name = name


def is_graph_declaration(value: Any) -> TypeGuard[type[Any]]:
    """Whether a value is a concrete ``Graph`` subclass."""
    from ...model.public.declarations import Graph

    return (
        isinstance(value, type)
        and issubclass(value, Graph)
        and value is not Graph
        and "_graph_options" in vars(value)
    )


def graph_name(value: type[Any]) -> str:
    """Return the portable name of a prepared graph declaration."""
    return value._graph_name


__all__ = [
    "graph_name", "is_graph_declaration", "prepare_graph_declaration",
]
