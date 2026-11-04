"""Author-facing generation request values."""
from __future__ import annotations

from dataclasses import dataclass, field

from .values import StaticValue


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """A statically discovered request attached to one asset declaration.

    The provider and configuration are stored as import coordinates, so
    discovery never imports the author-owned project. ``configuration`` holds
    the static literal keyword arguments, validated into the provider's
    ``CONFIG_TYPE`` when generation runs. ``package`` is the generated product's
    import package, and ``asset_module``/``asset_qualname`` locate the decorated
    asset class whose ``AssetOptions.layout`` the provider may use.
    ``asset_digest`` covers the asset source declaration, so editing a layout
    is a request change even though discovery never imports the class.

    Example:
        ```python
        from kg_build_system.generation.code_generation import GenerationRequest

        request = GenerationRequest(
            "project.providers", "PeopleProvider",
            "project.providers", "PeopleConfiguration",
            {"source": "../data/people.csv"},
            package="project.tables",
            asset_module="project.assets",
            asset_qualname="People",
        )
        ```
    """

    provider_module: str
    provider_qualname: str
    config_module: str
    config_qualname: str
    configuration: dict[str, StaticValue] = field(default_factory=dict)
    package: str = ""
    asset_module: str = ""
    asset_qualname: str = ""
    asset_digest: str = ""


__all__ = ["GenerationRequest"]
