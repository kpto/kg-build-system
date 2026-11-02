"""Read the blueprint a target compiler was given.

Compilation normally supplies the compatibility blueprint directly. A caller
that drives a compiler from a frozen build instead supplies the named language
parts, so this helper accepts both shapes without making every target restate
the distinction.
"""
from __future__ import annotations

from typing import Any

from ...compile.ir import BuildBlueprint


def _part(build: Any, name: str) -> Any:
    part = getattr(build, "part", None)
    if callable(part):
        return part(name)
    try:
        return build.parts[name]
    except (AttributeError, KeyError) as error:
        raise ValueError(f"build has no language part {name!r}") from error


def _members(value: Any, name: str) -> tuple[Any, ...]:
    members = getattr(value, name, None)
    return tuple(value if members is None else members)


def blueprint_from_context(context: Any) -> BuildBlueprint:
    """The blueprint a target compiler reads, from either context shape."""
    blueprint = getattr(context, "blueprint", None)
    if blueprint is not None:
        return blueprint
    build = getattr(context, "build", None)
    if build is None:
        raise ValueError("module compilation requires a blueprint or a build")
    data = _part(build, "data")
    topology = _part(build, "topology")
    binding = _part(build, "binding")
    return BuildBlueprint(
        structs=_members(data, "structs"),
        tables=_members(data, "tables"),
        components=_members(topology, "components"),
        projections=_members(data, "projections"),
        bindings=_members(binding, "bindings"),
        sources=_members(data, "sources"),
    )


__all__ = ["blueprint_from_context"]
