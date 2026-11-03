"""Read the frozen metadata owned by a topology declaration."""
from __future__ import annotations

from typing import Any

from ...model.internal.model.metadata import (
    ComponentMetadata,
    PropertyDeclaration,
)


def metadata_for(cls: type[Any]) -> ComponentMetadata | None:
    """The frozen declaration metadata owned by ``cls``, if any."""
    from .._private.metadata import metadata_for as read

    return read(cls)


def properties_for(cls: type[Any]) -> dict[str, PropertyDeclaration]:
    """Resolve inherited properties with Python shadowing semantics."""
    from .._private.metadata import properties_for as resolve

    return resolve(cls)


def component_kind(cls: type[Any]) -> str | None:
    """``"node"`` or ``"edge"`` when the class declares a component."""
    from .._private.metadata import component_kind as read

    return read(cls)


def is_abstract_component(cls: type[Any]) -> bool:
    """Whether the class declares an abstract category."""
    from .._private.metadata import is_abstract_component as check

    return check(cls)


def is_concrete_component(cls: type[Any]) -> bool:
    """Whether the class declares a concrete node or edge."""
    from .._private.metadata import is_concrete_component as check

    return check(cls)


__all__ = [
    "component_kind", "is_abstract_component", "is_concrete_component",
    "metadata_for", "properties_for",
]
