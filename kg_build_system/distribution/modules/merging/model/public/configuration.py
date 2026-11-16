"""The compatible-facts merging planner's configuration."""
from __future__ import annotations

import importlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict, cast

from kg_build_system.distribution.languages.topology.model.internal.model import (
    ComponentMetadata,
)
from kg_build_system.distribution.languages.topology.model.public import (
    TopologyDeclarationBase,
)
from kg_build_system.kernel import JsonValue
from kg_build_system.kernel.model.internal.json import FrozenObject, thaw_json


class ComponentReference(TypedDict):
    """The stored import coordinates of one configured component class.

    ``module`` and ``qualname`` locate the declaration without importing the
    author-owned project when the configuration is written; ``resolve_component``
    turns the pair back into the class.

    Example:
        ```python
        from kg_build_system.distribution.modules.merging.model.public import (
            ComponentReference,
        )

        reference: ComponentReference = {"module": "project.sites", "qualname": "Site"}
        ```
    """

    module: str
    qualname: str


class ComponentsDocument(TypedDict):
    """The stored component scope of a merging configuration.

    ``components`` is ``None`` for every record component, or the reference of
    each configured component class. The one fixed key keeps the document
    closed; it is not an open JSON object.

    Example:
        ```python
        from kg_build_system.distribution.modules.merging.model.public import (
            ComponentsDocument,
        )

        document: ComponentsDocument = {"components": None}
        ```
    """

    components: list[ComponentReference] | None


def resolve_component(
    value: type[object] | Mapping[str, JsonValue] | FrozenObject,
) -> type[object]:
    """Resolve one configured component class from a class or stored reference."""
    if isinstance(value, type):
        return value
    if isinstance(value, FrozenObject):
        value = thaw_json(value)
    if not isinstance(value, Mapping):
        raise TypeError("components must be concrete Node or Edge classes")
    module = importlib.import_module(str(value["module"]))
    component: object = module
    for part in str(value["qualname"]).split("."):
        component = getattr(component, part)
    return cast(type[object], component)


def resolve_components(
    components: tuple[
        type[object] | Mapping[str, JsonValue] | FrozenObject,
        ...,
    ] | None,
) -> tuple[type[TopologyDeclarationBase], ...] | None:
    """Resolve configured component references and check they are concrete."""
    if components is None:
        return None
    values = tuple(resolve_component(component) for component in components)
    for component in values:
        if not isinstance(component, type):
            raise TypeError("components must be concrete Node or Edge classes")
        declared = vars(component).get("_declaration")
        metadata = (
            declared if isinstance(declared, ComponentMetadata) else None
        )
        if (
            metadata is None
            or metadata.kind not in {"node", "edge"}
            or metadata.abstract
        ):
            raise TypeError("components must be concrete Node or Edge classes")
    return cast(tuple[type[TopologyDeclarationBase], ...], values)


def components_json(
    components: tuple[type[TopologyDeclarationBase], ...] | None,
) -> ComponentsDocument:
    """The JSON-compatible form of the configured component scope."""
    return {
        "components": (
            None if components is None
            else [
                ComponentReference(
                    module=component.__module__,
                    qualname=component.__qualname__,
                )
                for component in components
            ]
        ),
    }


@dataclass(frozen=True)
class MergingConfiguration:
    """Choose which record components are merged.

    ``components=None`` merges every record component; a tuple restricts the
    planner to those component classes, leaving every other component's records
    untouched by this step.

    Merging folds same-key rows into one record (a ``min()`` per column), so it
    is only sound for components whose parallel same-key rows are meant to be one
    fact. Edge families that deliberately keep parallel facts stay outside the
    scope.

    Example:
        ```python
        from kg_build_system.distribution import MergingConfiguration

        configuration = MergingConfiguration(components=(Site,))
        ```
    """

    components: tuple[type[TopologyDeclarationBase], ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "components", resolve_components(self.components))

    def to_json(self) -> ComponentsDocument:
        """Return the JSON-compatible component scope.

        Example:
            ```python
            document = MergingConfiguration().to_json()
            assert document == {"components": None}
            ```
        """
        return components_json(self.components)


__all__ = [
    "ComponentReference",
    "ComponentsDocument",
    "MergingConfiguration",
    "components_json",
    "resolve_component",
    "resolve_components",
]
